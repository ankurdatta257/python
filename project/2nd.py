import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
import webbrowser
from datetime import datetime, date


# ============================================================
# APPLYFLOW 3.0
# Career Application Management System
#
# Built with:
# Python + Tkinter + SQLite
#
# Portfolio Project
# ============================================================


APP_TITLE = "ApplyFlow"
DB_FILE = "applyflow.db"


# ============================================================
# DATABASE
# ============================================================

class Database:

    def __init__(self):
        self.connection = sqlite3.connect(DB_FILE)
        self.cursor = self.connection.cursor()

        self.create_table()
        self.seed_demo_data()

    def create_table(self):

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                location TEXT,
                status TEXT NOT NULL,
                deadline TEXT,
                applied_date TEXT,
                link TEXT,
                notes TEXT
            )
        """)

        self.connection.commit()

    def seed_demo_data(self):

        self.cursor.execute(
            "SELECT COUNT(*) FROM applications"
        )

        count = self.cursor.fetchone()[0]

        if count != 0:
            return

        demo_data = [

            (
                "Microsoft",
                "Software Engineering Intern",
                "Bangalore",
                "Interview",
                "2026-10-05",
                "2026-09-08",
                "https://careers.microsoft.com/",
                "Demo portfolio entry"
            ),

            (
                "Google",
                "Software Engineering Intern",
                "Bangalore",
                "Applied",
                "2026-10-12",
                "2026-09-10",
                "https://careers.google.com/",
                "Demo portfolio entry"
            ),

            (
                "Amazon",
                "Software Development Intern",
                "Hyderabad",
                "Saved",
                "2026-10-20",
                "",
                "https://www.amazon.jobs/",
                "Demo portfolio entry"
            ),

            (
                "Deloitte",
                "Technology Analyst Intern",
                "Mumbai",
                "Applied",
                "2026-09-30",
                "2026-09-12",
                "https://www.deloitte.com/",
                "Demo portfolio entry"
            ),

            (
                "Atlassian",
                "Backend Engineering Intern",
                "Remote",
                "Rejected",
                "2026-09-18",
                "2026-08-30",
                "https://www.atlassian.com/company/careers",
                "Demo portfolio entry"
            )
        ]

        self.cursor.executemany("""
            INSERT INTO applications
            (
                company,
                role,
                location,
                status,
                deadline,
                applied_date,
                link,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, demo_data)

        self.connection.commit()

    def get_all(self):

        self.cursor.execute("""
            SELECT *
            FROM applications
            ORDER BY
                CASE
                    WHEN deadline = '' THEN '9999-12-31'
                    ELSE deadline
                END
        """)

        return self.cursor.fetchall()

    def search(self, text="", status="All"):

        keyword = f"%{text}%"

        query = """
            SELECT *
            FROM applications
            WHERE
                company LIKE ?
                OR role LIKE ?
                OR location LIKE ?
        """

        params = [
            keyword,
            keyword,
            keyword
        ]

        if status != "All":

            query = """
                SELECT *
                FROM applications
                WHERE
                    (
                        company LIKE ?
                        OR role LIKE ?
                        OR location LIKE ?
                    )
                    AND status = ?
            """

            params.append(status)

        query += """
            ORDER BY
                CASE
                    WHEN deadline = '' THEN '9999-12-31'
                    ELSE deadline
                END
        """

        self.cursor.execute(
            query,
            params
        )

        return self.cursor.fetchall()

    def add(self, data):

        self.cursor.execute("""
            INSERT INTO applications
            (
                company,
                role,
                location,
                status,
                deadline,
                applied_date,
                link,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, data)

        self.connection.commit()

    def update(self, application_id, data):

        self.cursor.execute("""
            UPDATE applications
            SET
                company = ?,
                role = ?,
                location = ?,
                status = ?,
                deadline = ?,
                applied_date = ?,
                link = ?,
                notes = ?
            WHERE id = ?
        """, (*data, application_id))

        self.connection.commit()

    def delete(self, application_id):

        self.cursor.execute(
            "DELETE FROM applications WHERE id = ?",
            (application_id,)
        )

        self.connection.commit()

    def close(self):
        self.connection.close()


# ============================================================
# MAIN APPLICATION
# ============================================================

class ApplyFlow(tk.Tk):

    def __init__(self):

        super().__init__()

        self.title(
            "ApplyFlow — Career Command Center"
        )

        self.geometry(
            "1400x850"
        )

        self.minsize(
            1100,
            700
        )

        self.database = Database()

        self.dark_mode = True

        self.page = "Dashboard"

        self.setup_colors()

        self.setup_styles()

        self.build_interface()

        self.show_dashboard()

        self.protocol(
            "WM_DELETE_WINDOW",
            self.close_application
        )

    # ========================================================
    # COLOR SYSTEM
    # ========================================================

    def setup_colors(self):

        if self.dark_mode:

            self.colors = {

                "background": "#0B1220",
                "sidebar": "#0F172A",

                "surface": "#111C2E",
                "surface2": "#172338",

                "border": "#233149",

                "primary": "#6366F1",
                "primary_hover": "#818CF8",

                "text": "#F8FAFC",
                "muted": "#94A3B8",

                "green": "#22C55E",
                "yellow": "#F59E0B",
                "red": "#EF4444",
                "blue": "#38BDF8",

                "input": "#0F172A"
            }

        else:

            self.colors = {

                "background": "#F5F7FB",
                "sidebar": "#FFFFFF",

                "surface": "#FFFFFF",
                "surface2": "#F1F5F9",

                "border": "#E2E8F0",

                "primary": "#4F46E5",
                "primary_hover": "#6366F1",

                "text": "#0F172A",
                "muted": "#64748B",

                "green": "#16A34A",
                "yellow": "#D97706",
                "red": "#DC2626",
                "blue": "#0284C7",

                "input": "#FFFFFF"
            }

        self.configure(
            bg=self.colors["background"]
        )

    # ========================================================
    # TKINTER STYLES
    # ========================================================

    def setup_styles(self):

        style = ttk.Style(self)

        try:
            style.theme_use("clam")
        except:
            pass

        style.configure(
            "Treeview",
            background=self.colors["surface"],
            foreground=self.colors["text"],
            fieldbackground=self.colors["surface"],
            rowheight=46,
            borderwidth=0,
            font=("Segoe UI", 10)
        )

        style.configure(
            "Treeview.Heading",
            background=self.colors["surface2"],
            foreground=self.colors["muted"],
            font=("Segoe UI Semibold", 9),
            relief="flat"
        )

        style.map(
            "Treeview",
            background=[
                ("selected", self.colors["primary"])
            ],
            foreground=[
                ("selected", "#FFFFFF")
            ]
        )

        style.configure(
            "TCombobox",
            fieldbackground=self.colors["input"],
            background=self.colors["input"],
            foreground=self.colors["text"],
            borderwidth=0
        )

    # ========================================================
    # MAIN INTERFACE
    # ========================================================

    def build_interface(self):

        self.sidebar = tk.Frame(
            self,
            bg=self.colors["sidebar"],
            width=245
        )

        self.sidebar.pack(
            side="left",
            fill="y"
        )

        self.sidebar.pack_propagate(False)

        self.main = tk.Frame(
            self,
            bg=self.colors["background"]
        )

        self.main.pack(
            side="right",
            fill="both",
            expand=True
        )

        self.build_sidebar()

    # ========================================================
    # SIDEBAR
    # ========================================================

    def build_sidebar(self):

        # Logo

        logo_container = tk.Frame(
            self.sidebar,
            bg=self.colors["sidebar"]
        )

        logo_container.pack(
            fill="x",
            padx=25,
            pady=(30, 35)
        )

        logo_icon = tk.Label(
            logo_container,
            text="◆",
            font=("Segoe UI", 23, "bold"),
            fg=self.colors["primary"],
            bg=self.colors["sidebar"]
        )

        logo_icon.pack(
            side="left"
        )

        logo_text = tk.Label(
            logo_container,
            text=" ApplyFlow",
            font=("Segoe UI Semibold", 19),
            fg=self.colors["text"],
            bg=self.colors["sidebar"]
        )

        logo_text.pack(
            side="left"
        )

        # Workspace

        workspace = tk.Frame(
            self.sidebar,
            bg=self.colors["surface"],
            highlightthickness=1,
            highlightbackground=self.colors["border"]
        )

        workspace.pack(
            fill="x",
            padx=16,
            pady=(0, 25)
        )

        tk.Label(
            workspace,
            text="WORKSPACE",
            font=("Segoe UI Semibold", 8),
            fg=self.colors["muted"],
            bg=self.colors["surface"]
        ).pack(
            anchor="w",
            padx=15,
            pady=(12, 2)
        )

        tk.Label(
            workspace,
            text="Student Career Hub",
            font=("Segoe UI Semibold", 10),
            fg=self.colors["text"],
            bg=self.colors["surface"]
        ).pack(
            anchor="w",
            padx=15,
            pady=(0, 12)
        )

        # Navigation

        nav_title = tk.Label(
            self.sidebar,
            text="NAVIGATION",
            font=("Segoe UI Semibold", 8),
            fg=self.colors["muted"],
            bg=self.colors["sidebar"]
        )

        nav_title.pack(
            anchor="w",
            padx=25,
            pady=(0, 8)
        )

        self.navigation_buttons = {}

        navigation = [

            ("Dashboard", "⌂"),

            ("Applications", "▣"),

            ("Deadlines", "◷"),

            ("Analytics", "◈")

        ]

        for name, icon in navigation:

            button = tk.Button(
                self.sidebar,
                text=f"  {icon}    {name}",
                anchor="w",
                font=("Segoe UI", 10),
                fg=self.colors["muted"],
                bg=self.colors["sidebar"],
                activeforeground=self.colors["text"],
                activebackground=self.colors["surface2"],
                bd=0,
                padx=18,
                pady=13,
                cursor="hand2",
                command=lambda page=name:
                self.navigate(page)
            )

            button.pack(
                fill="x",
                padx=12,
                pady=2
            )

            self.navigation_buttons[name] = button

        # Bottom

        spacer = tk.Frame(
            self.sidebar,
            bg=self.colors["sidebar"]
        )

        spacer.pack(
            fill="both",
            expand=True
        )

        theme_button = tk.Button(
            self.sidebar,
            text="☾   Appearance",
            anchor="w",
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["sidebar"],
            activebackground=self.colors["surface2"],
            activeforeground=self.colors["text"],
            bd=0,
            padx=20,
            pady=12,
            command=self.toggle_theme
        )

        theme_button.pack(
            fill="x",
            padx=12
        )

        tk.Label(
            self.sidebar,
            text="ApplyFlow 3.0\nPython Portfolio Edition",
            font=("Segoe UI", 8),
            fg=self.colors["muted"],
            bg=self.colors["sidebar"],
            justify="left"
        ).pack(
            anchor="w",
            padx=25,
            pady=25
        )

    # ========================================================
    # NAVIGATION
    # ========================================================

    def navigate(self, page):

        self.page = page

        if page == "Dashboard":
            self.show_dashboard()

        elif page == "Applications":
            self.show_applications()

        elif page == "Deadlines":
            self.show_deadlines()

        elif page == "Analytics":
            self.show_analytics()

    # ========================================================
    # CLEAR MAIN
    # ========================================================

    def clear_main(self):

        for widget in self.main.winfo_children():
            widget.destroy()

    # ========================================================
    # HEADER
    # ========================================================

    def create_header(
        self,
        title,
        subtitle
    ):

        header = tk.Frame(
            self.main,
            bg=self.colors["background"]
        )

        header.pack(
            fill="x",
            padx=38,
            pady=(30, 22)
        )

        left = tk.Frame(
            header,
            bg=self.colors["background"]
        )

        left.pack(
            side="left"
        )

        tk.Label(
            left,
            text=title,
            font=("Segoe UI Semibold", 25),
            fg=self.colors["text"],
            bg=self.colors["background"]
        ).pack(
            anchor="w"
        )

        tk.Label(
            left,
            text=subtitle,
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["background"]
        ).pack(
            anchor="w",
            pady=(4, 0)
        )

        button = tk.Button(
            header,
            text="+  New Application",
            font=("Segoe UI Semibold", 10),
            bg=self.colors["primary"],
            fg="white",
            activebackground=self.colors["primary_hover"],
            activeforeground="white",
            bd=0,
            padx=20,
            pady=11,
            cursor="hand2",
            command=self.open_add_dialog
        )

        button.pack(
            side="right"
        )

    # ========================================================
    # DASHBOARD
    # ========================================================

    def show_dashboard(self):

        self.clear_main()

        self.create_header(
            "Good evening 👋",
            "Your career search, organized in one place."
        )

        data = self.database.get_all()

        total = len(data)

        applied = sum(
            1 for x in data
            if x[4] == "Applied"
        )

        interviews = sum(
            1 for x in data
            if x[4] == "Interview"
        )

        offers = sum(
            1 for x in data
            if x[4] == "Offer"
        )

        # ----------------------------------------------------
        # KPI CARDS
        # ----------------------------------------------------

        cards = tk.Frame(
            self.main,
            bg=self.colors["background"]
        )

        cards.pack(
            fill="x",
            padx=38
        )

        self.create_kpi(
            cards,
            "TOTAL APPLICATIONS",
            total,
            "All opportunities",
            self.colors["primary"]
        ).pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 8)
        )

        self.create_kpi(
            cards,
            "ACTIVE",
            applied + interviews,
            "Currently in process",
            self.colors["blue"]
        ).pack(
            side="left",
            fill="both",
            expand=True,
            padx=8
        )

        self.create_kpi(
            cards,
            "INTERVIEWS",
            interviews,
            "Interview stage",
            self.colors["yellow"]
        ).pack(
            side="left",
            fill="both",
            expand=True,
            padx=8
        )

        self.create_kpi(
            cards,
            "OFFERS",
            offers,
            "Successful outcomes",
            self.colors["green"]
        ).pack(
            side="left",
            fill="both",
            expand=True,
            padx=(8, 0)
        )

        # ----------------------------------------------------
        # LOWER SECTION
        # ----------------------------------------------------

        lower = tk.Frame(
            self.main,
            bg=self.colors["background"]
        )

        lower.pack(
            fill="both",
            expand=True,
            padx=38,
            pady=22
        )

        # Pipeline

        pipeline = self.card(
            lower
        )

        pipeline.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 10)
        )

        tk.Label(
            pipeline,
            text="Application Pipeline",
            font=("Segoe UI Semibold", 14),
            fg=self.colors["text"],
            bg=self.colors["surface"]
        ).pack(
            anchor="w",
            padx=22,
            pady=(20, 2)
        )

        tk.Label(
            pipeline,
            text="Where your applications currently stand",
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["surface"]
        ).pack(
            anchor="w",
            padx=22
        )

        statuses = [

            ("Saved", self.colors["muted"]),

            ("Applied", self.colors["primary"]),

            ("Interview", self.colors["yellow"]),

            ("Offer", self.colors["green"]),

            ("Rejected", self.colors["red"])

        ]

        for status, color in statuses:

            count = sum(
                1 for x in data
                if x[4] == status
            )

            row = tk.Frame(
                pipeline,
                bg=self.colors["surface"]
            )

            row.pack(
                fill="x",
                padx=22,
                pady=9
            )

            tk.Label(
                row,
                text=status,
                width=12,
                anchor="w",
                font=("Segoe UI", 9),
                fg=self.colors["text"],
                bg=self.colors["surface"]
            ).pack(
                side="left"
            )

            bar_background = tk.Frame(
                row,
                bg=self.colors["surface2"],
                height=8
            )

            bar_background.pack(
                side="left",
                fill="x",
                expand=True,
                padx=10
            )

            if total > 0:
                percentage = count / total
            else:
                percentage = 0

            bar_width = max(
                2,
                int(percentage * 260)
            )

            bar = tk.Frame(
                bar_background,
                bg=color,
                height=8,
                width=bar_width
            )

            bar.place(
                x=0,
                y=0
            )

            tk.Label(
                row,
                text=str(count),
                width=4,
                anchor="e",
                font=("Segoe UI Semibold", 9),
                fg=self.colors["text"],
                bg=self.colors["surface"]
            ).pack(
                side="right"
            )

        # Deadline section

        deadline_card = self.card(
            lower
        )

        deadline_card.pack(
            side="right",
            fill="both",
            expand=True,
            padx=(10, 0)
        )

        tk.Label(
            deadline_card,
            text="Upcoming Deadlines",
            font=("Segoe UI Semibold", 14),
            fg=self.colors["text"],
            bg=self.colors["surface"]
        ).pack(
            anchor="w",
            padx=22,
            pady=(20, 2)
        )

        tk.Label(
            deadline_card,
            text="Your next important dates",
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["surface"]
        ).pack(
            anchor="w",
            padx=22,
            pady=(0, 10)
        )

        upcoming = []

        today = date.today()

        for app in data:

            if not app[5]:
                continue

            try:

                deadline = datetime.strptime(
                    app[5],
                    "%Y-%m-%d"
                ).date()

                if deadline >= today:
                    upcoming.append(
                        (deadline, app)
                    )

            except:
                continue

        upcoming.sort(
            key=lambda x: x[0]
        )

        for deadline, app in upcoming[:5]:

            row = tk.Frame(
                deadline_card,
                bg=self.colors["surface"]
            )

            row.pack(
                fill="x",
                padx=22,
                pady=8
            )

            tk.Label(
                row,
                text=app[1],
                font=("Segoe UI Semibold", 9),
                fg=self.colors["text"],
                bg=self.colors["surface"]
            ).pack(
                anchor="w"
            )

            days = (
                deadline - today
            ).days

            if days == 0:

                urgency = "Today"
                urgency_color = self.colors["red"]

            elif days == 1:

                urgency = "Tomorrow"
                urgency_color = self.colors["yellow"]

            else:

                urgency = f"{days} days"
                urgency_color = self.colors["muted"]

            tk.Label(
                row,
                text=f"{deadline.strftime('%d %b %Y')}  •  {urgency}",
                font=("Segoe UI", 8),
                fg=urgency_color,
                bg=self.colors["surface"]
            ).pack(
                anchor="w"
            )

        if not upcoming:

            tk.Label(
                deadline_card,
                text="No upcoming deadlines.",
                font=("Segoe UI", 10),
                fg=self.colors["muted"],
                bg=self.colors["surface"]
            ).pack(
                pady=40
            )

    # ========================================================
    # KPI CARD
    # ========================================================

    def create_kpi(
        self,
        parent,
        title,
        value,
        description,
        accent
    ):

        frame = tk.Frame(
            parent,
            bg=self.colors["surface"],
            height=130,
            highlightthickness=1,
            highlightbackground=self.colors["border"]
        )

        frame.pack_propagate(False)

        top = tk.Frame(
            frame,
            bg=self.colors["surface"]
        )

        top.pack(
            fill="x",
            padx=18,
            pady=(17, 0)
        )

        tk.Label(
            top,
            text=title,
            font=("Segoe UI Semibold", 8),
            fg=self.colors["muted"],
            bg=self.colors["surface"]
        ).pack(
            side="left"
        )

        tk.Frame(
            top,
            bg=accent,
            width=7,
            height=7
        ).pack(
            side="right"
        )

        tk.Label(
            frame,
            text=str(value),
            font=("Segoe UI Semibold", 28),
            fg=self.colors["text"],
            bg=self.colors["surface"]
        ).pack(
            anchor="w",
            padx=18,
            pady=(7, 0)
        )

        tk.Label(
            frame,
            text=description,
            font=("Segoe UI", 8),
            fg=self.colors["muted"],
            bg=self.colors["surface"]
        ).pack(
            anchor="w",
            padx=18
        )

        return frame

    # ========================================================
    # APPLICATIONS PAGE
    # ========================================================

    def show_applications(self):

        self.clear_main()

        self.create_header(
            "Applications",
            "Manage and track every opportunity."
        )

        # Toolbar

        toolbar = tk.Frame(
            self.main,
            bg=self.colors["background"]
        )

        toolbar.pack(
            fill="x",
            padx=38,
            pady=(0, 15)
        )

        search_var = tk.StringVar()

        search = tk.Entry(
            toolbar,
            textvariable=search_var,
            font=("Segoe UI", 10),
            bg=self.colors["surface"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief="flat",
            width=38
        )

        search.pack(
            side="left",
            ipady=10
        )

        search.insert(
            0,
            "Search applications..."
        )

        status_var = tk.StringVar(
            value="All"
        )

        status_box = ttk.Combobox(
            toolbar,
            textvariable=status_var,
            values=[
                "All",
                "Saved",
                "Applied",
                "Interview",
                "Offer",
                "Rejected"
            ],
            state="readonly",
            width=15
        )

        status_box.pack(
            side="left",
            padx=10
        )

        export_button = tk.Button(
            toolbar,
            text="Export CSV",
            font=("Segoe UI Semibold", 9),
            bg=self.colors["surface"],
            fg=self.colors["text"],
            activebackground=self.colors["surface2"],
            bd=0,
            padx=16,
            pady=10,
            command=self.export_csv
        )

        export_button.pack(
            side="right"
        )

        # Table card

        table_card = self.card(
            self.main
        )

        table_card.pack(
            fill="both",
            expand=True,
            padx=38,
            pady=(0, 30)
        )

        columns = (
            "company",
            "role",
            "location",
            "status",
            "deadline"
        )

        tree = ttk.Treeview(
            table_card,
            columns=columns,
            show="headings"
        )

        headings = {

            "company": "Company",

            "role": "Position",

            "location": "Location",

            "status": "Status",

            "deadline": "Deadline"

        }

        widths = {

            "company": 180,

            "role": 300,

            "location": 150,

            "status": 130,

            "deadline": 140

        }

        for column in columns:

            tree.heading(
                column,
                text=headings[column]
            )

            tree.column(
                column,
                width=widths[column],
                anchor="w"
            )

        scrollbar = ttk.Scrollbar(
            table_card,
            orient="vertical",
            command=tree.yview
        )

        tree.configure(
            yscrollcommand=scrollbar.set
        )

        tree.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(15, 0),
            pady=15
        )

        scrollbar.pack(
            side="right",
            fill="y",
            pady=15,
            padx=(0, 15)
        )

        def refresh_table(*args):

            for item in tree.get_children():
                tree.delete(item)

            text = search_var.get()

            if text == "Search applications...":
                text = ""

            results = self.database.search(
                text,
                status_var.get()
            )

            for app in results:

                deadline = app[5]

                if deadline:

                    try:

                        deadline = datetime.strptime(
                            deadline,
                            "%Y-%m-%d"
                        ).strftime("%d %b %Y")

                    except:
                        pass

                tree.insert(
                    "",
                    "end",
                    iid=str(app[0]),
                    values=(
                        app[1],
                        app[2],
                        app[3],
                        app[4],
                        deadline
                    )
                )

        search.bind(
            "<KeyRelease>",
            refresh_table
        )

        status_box.bind(
            "<<ComboboxSelected>>",
            refresh_table
        )

        def edit_selected(event=None):

            selected = tree.selection()

            if not selected:
                return

            application_id = int(
                selected[0]
            )

            app = self.get_application(
                application_id
            )

            if app:
                self.open_edit_dialog(app)

        tree.bind(
            "<Double-1>",
            edit_selected
        )

        def right_click(event):

            item = tree.identify_row(
                event.y
            )

            if not item:
                return

            tree.selection_set(item)

            menu = tk.Menu(
                self,
                tearoff=0
            )

            menu.add_command(
                label="Edit Application",
                command=edit_selected
            )

            menu.add_command(
                label="Delete Application",
                command=lambda:
                self.delete_tree_application(tree)
            )

            menu.post(
                event.x_root,
                event.y_root
            )

        tree.bind(
            "<Button-3>",
            right_click
        )

        refresh_table()

    # ========================================================
    # GET APPLICATION
    # ========================================================

    def get_application(
        self,
        application_id
    ):

        for app in self.database.get_all():

            if app[0] == application_id:
                return app

        return None

    # ========================================================
    # DEADLINES PAGE
    # ========================================================

    def show_deadlines(self):

        self.clear_main()

        self.create_header(
            "Deadline Center",
            "Stay ahead of every important application date."
        )

        data = self.database.get_all()

        today = date.today()

        sections = {

            "Overdue": [],

            "Today": [],

            "Next 7 Days": [],

            "Upcoming": []

        }

        for app in data:

            if not app[5]:
                continue

            try:

                deadline = datetime.strptime(
                    app[5],
                    "%Y-%m-%d"
                ).date()

            except:
                continue

            days = (
                deadline - today
            ).days

            if days < 0:
                sections["Overdue"].append(app)

            elif days == 0:
                sections["Today"].append(app)

            elif days <= 7:
                sections["Next 7 Days"].append(app)

            else:
                sections["Upcoming"].append(app)

        container = tk.Frame(
            self.main,
            bg=self.colors["background"]
        )

        container.pack(
            fill="both",
            expand=True,
            padx=38
        )

        for section, applications in sections.items():

            card = self.card(
                container
            )

            card.pack(
                fill="x",
                pady=6
            )

            title_color = self.colors["text"]

            if section == "Overdue":
                title_color = self.colors["red"]

            elif section == "Today":
                title_color = self.colors["yellow"]

            tk.Label(
                card,
                text=f"{section}   {len(applications)}",
                font=("Segoe UI Semibold", 12),
                fg=title_color,
                bg=self.colors["surface"]
            ).pack(
                anchor="w",
                padx=20,
                pady=(15, 10)
            )

            if not applications:

                tk.Label(
                    card,
                    text="No applications in this section.",
                    font=("Segoe UI", 9),
                    fg=self.colors["muted"],
                    bg=self.colors["surface"]
                ).pack(
                    anchor="w",
                    padx=20,
                    pady=(0, 15)
                )

            for app in applications:

                row = tk.Frame(
                    card,
                    bg=self.colors["surface"]
                )

                row.pack(
                    fill="x",
                    padx=20,
                    pady=5
                )

                tk.Label(
                    row,
                    text=app[1],
                    width=25,
                    anchor="w",
                    font=("Segoe UI Semibold", 9),
                    fg=self.colors["text"],
                    bg=self.colors["surface"]
                ).pack(
                    side="left"
                )

                tk.Label(
                    row,
                    text=app[2],
                    width=35,
                    anchor="w",
                    font=("Segoe UI", 9),
                    fg=self.colors["muted"],
                    bg=self.colors["surface"]
                ).pack(
                    side="left"
                )

                tk.Label(
                    row,
                    text=app[5],
                    font=("Segoe UI Semibold", 9),
                    fg=self.colors["text"],
                    bg=self.colors["surface"]
                ).pack(
                    side="right"
                )

    # ========================================================
    # ANALYTICS
    # ========================================================

    def show_analytics(self):

        self.clear_main()

        self.create_header(
            "Analytics",
            "Measure the health of your application pipeline."
        )

        data = self.database.get_all()

        total = len(data)

        saved = sum(
            1 for x in data
            if x[4] == "Saved"
        )

        applied = sum(
            1 for x in data
            if x[4] == "Applied"
        )

        interview = sum(
            1 for x in data
            if x[4] == "Interview"
        )

        offer = sum(
            1 for x in data
            if x[4] == "Offer"
        )

        rejected = sum(
            1 for x in data
            if x[4] == "Rejected"
        )

        responses = (
            interview + offer
        )

        response_rate = (
            responses / applied * 100
            if applied > 0
            else 0
        )

        offer_rate = (
            offer / applied * 100
            if applied > 0
            else 0
        )

        # Metrics

        metrics = tk.Frame(
            self.main,
            bg=self.colors["background"]
        )

        metrics.pack(
            fill="x",
            padx=38
        )

        self.analytics_metric(
            metrics,
            "Response Rate",
            f"{response_rate:.1f}%",
            "Interviews + offers"
        ).pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 8)
        )

        self.analytics_metric(
            metrics,
            "Offer Rate",
            f"{offer_rate:.1f}%",
            "Offers / applications"
        ).pack(
            side="left",
            fill="both",
            expand=True,
            padx=8
        )

        self.analytics_metric(
            metrics,
            "Interviews",
            interview,
            "Current interview stage"
        ).pack(
            side="left",
            fill="both",
            expand=True,
            padx=8
        )

        self.analytics_metric(
            metrics,
            "Total",
            total,
            "Tracked opportunities"
        ).pack(
            side="left",
            fill="both",
            expand=True,
            padx=(8, 0)
        )

        # Chart

        chart_card = self.card(
            self.main
        )

        chart_card.pack(
            fill="both",
            expand=True,
            padx=38,
            pady=25
        )

        tk.Label(
            chart_card,
            text="Pipeline Overview",
            font=("Segoe UI Semibold", 15),
            fg=self.colors["text"],
            bg=self.colors["surface"]
        ).pack(
            anchor="w",
            padx=25,
            pady=(20, 0)
        )

        tk.Label(
            chart_card,
            text="Application distribution by stage",
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["surface"]
        ).pack(
            anchor="w",
            padx=25
        )

        chart = tk.Canvas(
            chart_card,
            bg=self.colors["surface"],
            highlightthickness=0
        )

        chart.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=15
        )

        chart_data = [

            ("Saved", saved, self.colors["muted"]),

            ("Applied", applied, self.colors["primary"]),

            ("Interview", interview, self.colors["yellow"]),

            ("Offer", offer, self.colors["green"]),

            ("Rejected", rejected, self.colors["red"])

        ]

        def draw_chart(event=None):

            chart.delete("all")

            width = chart.winfo_width()
            height = chart.winfo_height()

            if width < 300:
                return

            max_value = max(
                1,
                max(
                    value
                    for _, value, _ in chart_data
                )
            )

            baseline = height - 60

            bar_width = 65

            spacing = max(
                100,
                (width - 150) // len(chart_data)
            )

            start = 70

            for index, (
                label,
                value,
                color
            ) in enumerate(chart_data):

                x = (
                    start +
                    index * spacing
                )

                available_height = (
                    height - 130
                )

                bar_height = (
                    value /
                    max_value *
                    available_height
                )

                chart.create_rectangle(
                    x,
                    baseline - bar_height,
                    x + bar_width,
                    baseline,
                    fill=color,
                    outline=""
                )

                chart.create_text(
                    x + bar_width / 2,
                    baseline + 20,
                    text=label,
                    fill=self.colors["muted"],
                    font=("Segoe UI", 9)
                )

                chart.create_text(
                    x + bar_width / 2,
                    baseline - bar_height - 15,
                    text=str(value),
                    fill=self.colors["text"],
                    font=("Segoe UI Semibold", 11)
                )

            chart.create_line(
                40,
                baseline,
                width - 30,
                baseline,
                fill=self.colors["border"]
            )

        chart.bind(
            "<Configure>",
            draw_chart
        )

        self.after(
            100,
            draw_chart
        )

    # ========================================================
    # ANALYTICS METRIC
    # ========================================================

    def analytics_metric(
        self,
        parent,
        title,
        value,
        subtitle
    ):

        frame = tk.Frame(
            parent,
            bg=self.colors["surface"],
            height=120,
            highlightthickness=1,
            highlightbackground=self.colors["border"]
        )

        frame.pack_propagate(False)

        tk.Label(
            frame,
            text=title,
            font=("Segoe UI Semibold", 8),
            fg=self.colors["muted"],
            bg=self.colors["surface"]
        ).pack(
            anchor="w",
            padx=18,
            pady=(16, 0)
        )

        tk.Label(
            frame,
            text=str(value),
            font=("Segoe UI Semibold", 25),
            fg=self.colors["text"],
            bg=self.colors["surface"]
        ).pack(
            anchor="w",
            padx=18
        )

        tk.Label(
            frame,
            text=subtitle,
            font=("Segoe UI", 8),
            fg=self.colors["muted"],
            bg=self.colors["surface"]
        ).pack(
            anchor="w",
            padx=18
        )

        return frame

    # ========================================================
    # CARD
    # ========================================================

    def card(self, parent):

        return tk.Frame(
            parent,
            bg=self.colors["surface"],
            highlightthickness=1,
            highlightbackground=self.colors["border"]
        )

    # ========================================================
    # ADD APPLICATION
    # ========================================================

    def open_add_dialog(self):

        self.open_form()

    # ========================================================
    # EDIT APPLICATION
    # ========================================================

    def open_edit_dialog(self, application):

        self.open_form(
            application
        )

    # ========================================================
    # FORM
    # ========================================================

    def open_form(
        self,
        application=None
    ):

        dialog = tk.Toplevel(
            self
        )

        dialog.title(
            "Edit Application"
            if application
            else "New Application"
        )

        dialog.geometry(
            "560x720"
        )

        dialog.configure(
            bg=self.colors["background"]
        )

        dialog.transient(
            self
        )

        dialog.grab_set()

        form = tk.Frame(
            dialog,
            bg=self.colors["surface"]
        )

        form.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=25
        )

        title = (
            "Edit Application"
            if application
            else "New Application"
        )

        tk.Label(
            form,
            text=title,
            font=("Segoe UI Semibold", 20),
            fg=self.colors["text"],
            bg=self.colors["surface"]
        ).pack(
            anchor="w",
            padx=25,
            pady=(22, 3)
        )

        tk.Label(
            form,
            text="Add the details you need to keep your search organized.",
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["surface"]
        ).pack(
            anchor="w",
            padx=25,
            pady=(0, 18)
        )

        fields = {}

        field_list = [

            ("Company", "company"),

            ("Position", "role"),

            ("Location", "location"),

            ("Deadline  •  YYYY-MM-DD", "deadline"),

            ("Applied Date  •  YYYY-MM-DD", "applied_date"),

            ("Application URL", "link")

        ]

        for label, key in field_list:

            tk.Label(
                form,
                text=label,
                font=("Segoe UI Semibold", 8),
                fg=self.colors["muted"],
                bg=self.colors["surface"]
            ).pack(
                anchor="w",
                padx=25,
                pady=(7, 4)
            )

            entry = tk.Entry(
                form,
                bg=self.colors["input"],
                fg=self.colors["text"],
                insertbackground=self.colors["text"],
                relief="flat",
                font=("Segoe UI", 9)
            )

            entry.pack(
                fill="x",
                padx=25,
                ipady=8
            )

            fields[key] = entry

        # Status

        tk.Label(
            form,
            text="Status",
            font=("Segoe UI Semibold", 8),
            fg=self.colors["muted"],
            bg=self.colors["surface"]
        ).pack(
            anchor="w",
            padx=25,
            pady=(8, 4)
        )

        status = ttk.Combobox(
            form,
            values=[
                "Saved",
                "Applied",
                "Interview",
                "Offer",
                "Rejected"
            ],
            state="readonly"
        )

        status.pack(
            fill="x",
            padx=25
        )

        fields["status"] = status

        # Notes

        tk.Label(
            form,
            text="Notes",
            font=("Segoe UI Semibold", 8),
            fg=self.colors["muted"],
            bg=self.colors["surface"]
        ).pack(
            anchor="w",
            padx=25,
            pady=(8, 4)
        )

        notes = tk.Text(
            form,
            height=4,
            bg=self.colors["input"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief="flat",
            font=("Segoe UI", 9)
        )

        notes.pack(
            fill="x",
            padx=25
        )

        fields["notes"] = notes

        # Fill existing data

        if application:

            values = {

                "company": application[1],

                "role": application[2],

                "location": application[3],

                "deadline": application[5],

                "applied_date": application[6],

                "link": application[7]

            }

            for key, value in values.items():

                fields[key].insert(
                    0,
                    value or ""
                )

            status.set(
                application[4]
            )

            notes.insert(
                "1.0",
                application[8] or ""
            )

        else:

            status.set(
                "Saved"
            )

        # Save

        def save():

            company = fields[
                "company"
            ].get().strip()

            role = fields[
                "role"
            ].get().strip()

            if not company or not role:

                messagebox.showwarning(
                    "Missing information",
                    "Company and Position are required.",
                    parent=dialog
                )

                return

            deadline = fields[
                "deadline"
            ].get().strip()

            applied_date = fields[
                "applied_date"
            ].get().strip()

            for value, name in [

                (deadline, "Deadline"),

                (applied_date, "Applied Date")

            ]:

                if value:

                    try:

                        datetime.strptime(
                            value,
                            "%Y-%m-%d"
                        )

                    except ValueError:

                        messagebox.showwarning(
                            "Invalid date",
                            f"{name} must use YYYY-MM-DD.",
                            parent=dialog
                        )

                        return

            notes_text = notes.get(
                "1.0",
                "end"
            ).strip()

            data = (

                company,

                role,

                fields[
                    "location"
                ].get().strip(),

                status.get(),

                deadline,

                applied_date,

                fields[
                    "link"
                ].get().strip(),

                notes_text

            )

            if application:

                self.database.update(
                    application[0],
                    data
                )

            else:

                self.database.add(
                    data
                )

            dialog.destroy()

            self.navigate(
                self.page
            )

        save_button = tk.Button(
            form,
            text=(
                "Save Changes"
                if application
                else "Create Application"
            ),
            bg=self.colors["primary"],
            fg="white",
            activebackground=self.colors["primary_hover"],
            activeforeground="white",
            font=("Segoe UI Semibold", 10),
            bd=0,
            padx=20,
            pady=11,
            cursor="hand2",
            command=save
        )

        save_button.pack(
            anchor="e",
            padx=25,
            pady=20
        )

    # ========================================================
    # DELETE
    # ========================================================

    def delete_tree_application(
        self,
        tree
    ):

        selected = tree.selection()

        if not selected:
            return

        application_id = int(
            selected[0]
        )

        confirm = messagebox.askyesno(
            "Delete Application",
            "Delete this application permanently?"
        )

        if confirm:

            self.database.delete(
                application_id
            )

            self.show_applications()

    # ========================================================
    # EXPORT CSV
    # ========================================================

    def export_csv(self):

        data = self.database.get_all()

        if not data:

            messagebox.showinfo(
                "Export",
                "There are no applications to export."
            )

            return

        filename = filedialog.asksaveasfilename(

            title="Export ApplyFlow Data",

            defaultextension=".csv",

            filetypes=[
                ("CSV files", "*.csv")
            ]

        )

        if not filename:
            return

        with open(
            filename,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.writer(
                file
            )

            writer.writerow([

                "ID",

                "Company",

                "Position",

                "Location",

                "Status",

                "Deadline",

                "Applied Date",

                "Application URL",

                "Notes"

            ])

            writer.writerows(
                data
            )

        messagebox.showinfo(
            "Export Complete",
            "Your ApplyFlow data was exported successfully."
        )

    # ========================================================
    # THEME
    # ========================================================

    def toggle_theme(self):

        self.dark_mode = not self.dark_mode

        self.setup_colors()

        self.setup_styles()

        for widget in self.winfo_children():
            widget.destroy()

        self.build_interface()

        self.navigate(
            self.page
        )

    # ========================================================
    # CLOSE
    # ========================================================

    def close_application(self):

        self.database.close()

        self.destroy()


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    application = ApplyFlow()

    application.mainloop()