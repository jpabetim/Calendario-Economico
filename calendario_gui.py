# calendario_gui.py

import tkinter as tk
from tkinter import ttk, messagebox, PhotoImage
from tkcalendar import DateEntry
from datetime import datetime, timedelta, date
import pandas as pd
import threading
import queue
from ttkthemes import ThemedTk
import os

from economic_calendar import get_economic_calendar

class CalendarioEconomicoApp(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        # ... (código de __init__ sin cambios)
        self.parent = parent; self.parent.title("Calendario Económico - TraidingRoad-AI"); self.center_window(1200, 700)
        try:
            icon_path = os.path.join(os.path.dirname(__file__), 'icono.png'); self.parent.iconphoto(True, PhotoImage(file=icon_path))
        except tk.TclError: print("No se encontró 'icono.png'. Se usará el icono por defecto.")
        self.parent.columnconfigure(0, weight=1); self.parent.rowconfigure(0, weight=1); self.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1); self.rowconfigure(1, weight=1)
        self.full_data_df = pd.DataFrame(); self.data_queue = queue.Queue()
        self.event_item_map = {}; self.is_first_load = True; self._update_job = None 
        self.crear_widgets_filtros(); self.crear_tabla_eventos(); self.configurar_estilos()
        self.obtener_datos_en_hilo(); self.process_queue()

    def center_window(self, width, height): #... sin cambios
        screen_width = self.parent.winfo_screenwidth(); screen_height = self.parent.winfo_screenheight()
        x = (screen_width/2) - (width/2); y = (screen_height/2) - (height/2)
        self.parent.geometry('%dx%d+%d+%d' % (width, height, x, y))

    def crear_widgets_filtros(self): #... sin cambios
        frame_filtros = ttk.LabelFrame(self, text="Filtros"); frame_filtros.grid(row=0, column=0, sticky="ew", padx=10, pady=(10,5)); frame_filtros.columnconfigure(1, weight=1)
        frame_fechas = ttk.Frame(frame_filtros); frame_fechas.grid(row=0, column=0, sticky='w', padx=5, pady=5)
        ttk.Label(frame_fechas, text="Desde:").grid(row=0, column=0, pady=2, padx=(0,5))
        self.fecha_inicio_entry = DateEntry(frame_fechas, date_pattern='y-mm-dd', width=12); self.fecha_inicio_entry.set_date(datetime.now()); self.fecha_inicio_entry.grid(row=0, column=1, padx=5)
        ttk.Label(frame_fechas, text="Hasta:").grid(row=1, column=0, pady=2, padx=(0,5))
        self.fecha_fin_entry = DateEntry(frame_fechas, date_pattern='y-mm-dd', width=12); self.fecha_fin_entry.set_date(datetime.now() + timedelta(days=7)); self.fecha_fin_entry.grid(row=1, column=1, padx=5)
        frame_botones_fecha = ttk.Frame(frame_fechas); frame_botones_fecha.grid(row=0, column=2, rowspan=2, padx=(15, 0))
        style = ttk.Style(); style.configure("Quick.TButton", padding=5, font=('Segoe UI', 8))
        ttk.Button(frame_botones_fecha, text="Hoy", command=self.set_date_today, style="Quick.TButton").pack(fill='x')
        ttk.Button(frame_botones_fecha, text="Esta Semana", command=self.set_date_this_week, style="Quick.TButton").pack(fill='x', pady=2)
        ttk.Button(frame_botones_fecha, text="Este Mes", command=self.set_date_this_month, style="Quick.TButton").pack(fill='x')
        frame_opciones_der = ttk.Frame(frame_filtros); frame_opciones_der.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)
        frame_impacto = ttk.LabelFrame(frame_opciones_der, text="Impacto"); frame_impacto.pack(side=tk.LEFT, padx=(0,10), fill=tk.Y)
        self.impacto_vars = {'high': tk.BooleanVar(value=True), 'medium': tk.BooleanVar(value=True), 'low': tk.BooleanVar(value=False)}
        ttk.Checkbutton(frame_impacto, text="Alto", variable=self.impacto_vars['high'], command=self.aplicar_filtros_locales).pack(anchor='w')
        ttk.Checkbutton(frame_impacto, text="Medio", variable=self.impacto_vars['medium'], command=self.aplicar_filtros_locales).pack(anchor='w')
        ttk.Checkbutton(frame_impacto, text="Bajo", variable=self.impacto_vars['low'], command=self.aplicar_filtros_locales).pack(anchor='w')
        frame_paises_container = ttk.LabelFrame(frame_opciones_der, text="Países"); frame_paises_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        frame_paises_container.rowconfigure(0, weight=1); frame_paises_container.columnconfigure(0, weight=1)
        canvas = tk.Canvas(frame_paises_container, borderwidth=0); scrollbar = ttk.Scrollbar(frame_paises_container, orient="vertical", command=canvas.yview)
        self.scrollable_frame_paises = ttk.Frame(canvas); self.scrollable_frame_paises.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scrollable_frame_paises, anchor="nw"); canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky='nsew'); scrollbar.grid(row=0, column=1, sticky='ns'); self.paises_vars = {} 
        controles_app_frame = ttk.Frame(frame_filtros); controles_app_frame.grid(row=0, column=2, sticky='ne', padx=5, pady=5)
        self.boton_fetch = ttk.Button(controles_app_frame, text="Actualizar", command=self.obtener_datos_en_hilo); self.boton_fetch.pack(pady=2, fill='x')
        self.ver_pasados_var = tk.BooleanVar(value=False)
        ver_pasados_check = ttk.Checkbutton(controles_app_frame, text="Ver eventos pasados", variable=self.ver_pasados_var, command=self.aplicar_filtros_locales); ver_pasados_check.pack(pady=2, anchor='w')
        self.status_label = ttk.Label(controles_app_frame, text="Cargando...", foreground="blue"); self.status_label.pack(pady=2, anchor='w', side='bottom')

    def set_date_range_and_refresh(self, start_date, end_date): #... sin cambios
        self.fecha_inicio_entry.set_date(start_date); self.fecha_fin_entry.set_date(end_date)
        self.obtener_datos_en_hilo()

    def set_date_today(self):
        """CORRECCIÓN 1: La fecha 'Hasta' debe ser igual o posterior a 'Desde'."""
        today = date.today()
        # Para evitar el error de investpy, si pedimos hoy, pedimos un rango de 24h
        tomorrow = today + timedelta(days=1)
        self.set_date_range_and_refresh(today, tomorrow)

    def set_date_this_week(self): #... sin cambios
        today = date.today(); start_of_week = today - timedelta(days=today.weekday()); end_of_week = start_of_week + timedelta(days=6)
        self.set_date_range_and_refresh(start_of_week, end_of_week)

    def set_date_this_month(self): #... sin cambios
        today = date.today(); start_of_month = today.replace(day=1)
        next_month_year = start_of_month.year if start_of_month.month < 12 else start_of_month.year + 1
        next_month_month = start_of_month.month + 1 if start_of_month.month < 12 else 1
        end_of_month = date(next_month_year, next_month_month, 1) - timedelta(days=1)
        self.set_date_range_and_refresh(start_of_month, end_of_month)

    def actualizar_filtro_paises(self): #... sin cambios
        for widget in self.scrollable_frame_paises.winfo_children(): widget.destroy()
        if self.full_data_df.empty: ttk.Label(self.scrollable_frame_paises, text="Sin datos.").pack(); return
        paises = sorted(self.full_data_df['País'].unique()); paises_seleccionados_antes = {pais for pais, var in self.paises_vars.items() if var.get()}; self.paises_vars.clear()
        num_columnas = 4
        for i, pais in enumerate(paises):
            var = tk.BooleanVar()
            if self.is_first_load and pais in ['United States', 'Euro Zone', 'Japan', 'United Kingdom']: var.set(True)
            elif pais in paises_seleccionados_antes: var.set(True)
            cb = ttk.Checkbutton(self.scrollable_frame_paises, text=pais, variable=var, command=self.aplicar_filtros_locales)
            fila, columna = divmod(i, num_columnas); cb.grid(row=fila, column=columna, sticky='w', padx=5); self.paises_vars[pais] = var

    def crear_tabla_eventos(self): #... sin cambios
        frame_tabla = ttk.Frame(self); frame_tabla.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        frame_tabla.columnconfigure(0, weight=1); frame_tabla.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(frame_tabla, columns=('Fecha y Hora', 'País', 'Evento', 'Impacto', 'Actual', 'Consenso', 'Previo'), show='headings')
        for col in self.tree['columns']: self.tree.heading(col, text=col, anchor='center')
        self.tree.column("Fecha y Hora", width=140, anchor='w'); self.tree.column("País", width=150, anchor='w'); self.tree.column("Evento", width=400, anchor='w')
        self.tree.column("Impacto", width=80, anchor='center'); self.tree.column("Actual", width=80, anchor='center')
        self.tree.column("Consenso", width=80, anchor='center'); self.tree.column("Previo", width=80, anchor='center')
        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky='nsew'); scrollbar.grid(row=0, column=1, sticky='ns')

    def configurar_estilos(self): #... sin cambios
        style = ttk.Style(); style.configure("Treeview", rowheight=25, font=('Segoe UI', 9)); style.configure("Treeview.Heading", font=('Segoe UI', 10, 'bold'))
        style.map("Treeview", background=[('selected', '#004A99')], foreground=[('selected', 'white')])
        self.tree.tag_configure('high', background='#FFCDD2'); self.tree.tag_configure('medium', background='#FFECB3'); self.tree.tag_configure('low', background='#E8F5E9')

    def obtener_datos_en_hilo(self): #... sin cambios
        self.status_label.config(text="Actualizando..."); self.boton_fetch.config(state="disabled")
        worker = threading.Thread(target=self.data_worker_task, daemon=True); worker.start()
        
    def data_worker_task(self): #... sin cambios
        fecha_inicio_str = self.fecha_inicio_entry.get_date().strftime('%Y-%m-%d'); fecha_fin_str = self.fecha_fin_entry.get_date().strftime('%Y-%m-%d')
        df = get_economic_calendar(fecha_inicio_str, fecha_fin_str)
        self.data_queue.put(df)

    def process_queue(self): #... sin cambios
        try:
            new_df = self.data_queue.get_nowait()
            if not new_df.equals(self.full_data_df):
                print("Nuevos datos detectados. Actualizando la tabla..."); self.full_data_df = new_df;
                if self.is_first_load: self.actualizar_filtro_paises()
                self.aplicar_filtros_locales()
            else: print(f"Datos comprobados a las {datetime.now().strftime('%H:%M:%S')}. Sin cambios.")
            self.boton_fetch.config(state="normal")
            if self.is_first_load: self.is_first_load = False
            self.schedule_next_update()
        except queue.Empty: pass
        finally: self.parent.after(200, self.process_queue) 

    def schedule_next_update(self):
        """CORRECCIÓN 2: Añadimos una guarda para evitar el error si el DataFrame está vacío."""
        if self._update_job: self.parent.after_cancel(self._update_job)
        
        # Si no hay datos, no podemos planificar la siguiente actualización basada en eventos
        if self.full_data_df.empty:
            self.status_label.config(text="Error de datos. Reintentando en 60s.")
            self._update_job = self.parent.after(60000, self.obtener_datos_en_hilo)
            return

        now = datetime.now(); futuros = self.full_data_df[self.full_data_df['Fecha y Hora'] > now]
        next_refresh_seconds = 60
        if not futuros.empty:
            next_event_time = futuros['Fecha y Hora'].iloc[0]; delta_seconds = (next_event_time - now).total_seconds()
            if delta_seconds < 600: next_refresh_seconds = 10
            self.status_label.config(text=f"Próx. act. en {next_refresh_seconds}s")
        else: self.status_label.config(text=f"Actualizado: {datetime.now().strftime('%H:%M:%S')}")
        self._update_job = self.parent.after(next_refresh_seconds * 1000, self.obtener_datos_en_hilo)

    def aplicar_filtros_locales(self, event=None): #... sin cambios
        if self.full_data_df.empty:
            for item in self.tree.get_children(): self.tree.delete(item)
            self.event_item_map.clear(); return
        df_filtrado = self.full_data_df.copy()
        if not self.ver_pasados_var.get():
            # Comparamos con la zona horaria correcta
            now_aware = datetime.now(self.full_data_df['Fecha y Hora'].iloc[0].tz)
            df_filtrado = df_filtrado[df_filtrado['Fecha y Hora'] >= now_aware]
        impactos_seleccionados = {impacto for impacto, var in self.impacto_vars.items() if var.get()}
        if impactos_seleccionados: df_filtrado = df_filtrado[df_filtrado['Impacto'].isin(impactos_seleccionados)]
        paises_seleccionados = [pais for pais, var in self.paises_vars.items() if var.get()]
        if paises_seleccionados: df_filtrado = df_filtrado[df_filtrado['País'].isin(paises_seleccionados)]
        self.actualizar_tabla_inteligente(df_filtrado)

    def actualizar_tabla_inteligente(self, df_a_mostrar): #... sin cambios
        df_a_mostrar = df_a_mostrar.sort_values(by='Fecha y Hora', ascending=True)
        eventos_en_tabla = set(self.event_item_map.keys()); nuevos_eventos = set()
        for index, row in df_a_mostrar.iterrows():
            evento_id = (row['Fecha y Hora'], row['País'], row['Evento'])
            nuevos_eventos.add(evento_id)
            valores = list(row); valores[0] = row['Fecha y Hora'].strftime('%Y-%m-%d %H:%M')
            tag_color = row['Impacto'] if pd.notna(row['Impacto']) else ""
            if evento_id in self.event_item_map:
                item_id = self.event_item_map[evento_id]; self.tree.item(item_id, values=valores, tags=(tag_color,))
            else:
                item_id = self.tree.insert("", "end", values=valores, tags=(tag_color,)); self.event_item_map[evento_id] = item_id
        eventos_a_eliminar = eventos_en_tabla - nuevos_eventos
        for evento_id in eventos_a_eliminar:
            if evento_id in self.event_item_map:
                item_id = self.event_item_map[evento_id]
                if self.tree.exists(item_id): self.tree.delete(item_id)
                del self.event_item_map[evento_id]

if __name__ == "__main__":
    root = ThemedTk(theme="arc")
    app = CalendarioEconomicoApp(parent=root)
    root.mainloop()