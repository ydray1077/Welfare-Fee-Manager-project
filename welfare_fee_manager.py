import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import csv
import json
import os
import sys
import platform
from tkinter import PhotoImage

# Try to import PIL for JPG support
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# File to persistently store the welfare payers list
PERSIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'welfare_payers.json')

# --- Tooltip Helper ---
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)
    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left', background="#ffffe0", relief='solid', borderwidth=1, font=("Arial", 10))
        label.pack(ipadx=6, ipady=2)
    def hide_tip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

# --- Logic Layer ---
def extract_students_from_csv(file_path, id_col, name_col=None, email_col=None):
    """
    Extracts student info from a CSV file.
    Returns a dict: id -> {'id': id, 'name': name, 'email': email}
    """
    students = {}
    with open(file_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            id_val = row.get(id_col, '').strip()
            if id_val.isdigit() and 7 <= len(id_val) <= 10:
                name_val = row.get(name_col, '').strip() if name_col else ''
                email_val = row.get(email_col, '').strip() if email_col else ''
                students[id_val] = {'id': id_val, 'name': name_val, 'email': email_val}
    return students

def save_payers_list(students):
    """Save the welfare payers list to a local JSON file."""
    with open(PERSIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(students, f, ensure_ascii=False, indent=2)

def load_payers_list():
    """Load the welfare payers list from the local JSON file, if it exists."""
    if os.path.exists(PERSIST_FILE):
        with open(PERSIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def compare_students(master_dict, compare_dict):
    """
    Compare two dicts of students by ID.
    Returns (in_payers, not_in_payers) as lists of dicts.
    """
    in_payers = [compare_dict[id_] for id_ in compare_dict if id_ in master_dict]
    not_in_payers = [compare_dict[id_] for id_ in compare_dict if id_ not in master_dict]
    return in_payers, not_in_payers

def export_students_to_csv(students, file_path):
    """Export a list of student dicts to a CSV file. ID is always exported as an integer string."""
    with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['ID', 'Name', 'Email'])
        for s in students:
            id_val = s.get('id', '')
            # Remove decimal if present (e.g., '123456789.0' -> '123456789')
            try:
                id_val = str(int(float(id_val)))
            except Exception:
                id_val = str(id_val)
            writer.writerow([id_val, s.get('name', ''), s.get('email', '')])

# --- GUI Layer ---
class WelfareFeeApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Student Welfare Fee Manager - מנהל רווחה לסטודנטים')
        self.root.geometry('1100x750')
        self.root.resizable(False, False)
        self.set_rtl_support()
        self.setup_style()

        # Data
        self.payers = load_payers_list()  # dict: id -> {id, name, email}
        self.in_payers = []  # list of dicts
        self.not_in_payers = []  # list of dicts

        # UI
        self.logo_img = None  # Keep reference to avoid garbage collection
        self.create_widgets()
        self.refresh_payers_count()

    def set_rtl_support(self):
        # Set RTL direction for Hebrew support (works on Windows, partial on Linux/Mac)
        if platform.system() == 'Windows':
            self.root.option_add('*font', 'Arial 12')
        else:
            self.root.option_add('*font', 'Arial 12')
        # Tkinter does not have full RTL support, but we can align text to the right

    def setup_style(self):
        style = ttk.Style()
        style.theme_use('clam')
        # Soft color palette
        style.configure('TFrame', background='#f7f7fa')
        style.configure('TLabel', background='#f7f7fa', font=('Arial', 12))
        style.configure('Header.TLabel', font=('Arial', 18, 'bold'), background='#e3eafc', foreground='#2d3a4a', padding=10)
        style.configure('Section.TLabelframe', background='#e3eafc', borderwidth=2, relief='ridge')
        style.configure('Section.TLabelframe.Label', font=('Arial', 14, 'bold'), background='#e3eafc', foreground='#2d3a4a')
        style.configure('TButton', font=('Arial', 12), padding=6, background='#e3eafc', foreground='#2d3a4a')
        style.map('TButton', background=[('active', '#d0e2ff')])
        style.configure('Treeview', font=('Arial', 12), rowheight=28, fieldbackground='#f7f7fa', background='#f7f7fa')
        style.configure('Treeview.Heading', font=('Arial', 13, 'bold'), background='#e3eafc', foreground='#2d3a4a')

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, style='TFrame')
        main_frame.pack(fill='both', expand=True)

        # Logo (centered, enlarged, supports PNG and JPG)
        logo_path = None
        for fname in ['logo.png', 'logo.jpg', 'logo.jpeg']:
            candidate = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
            if os.path.exists(candidate):
                logo_path = candidate
                break
        if logo_path:
            try:
                if logo_path.lower().endswith('.png'):
                    img = PhotoImage(file=logo_path)
                    w, h = img.width(), img.height()
                    factor = max(w // 128, h // 128, 1)
                    if factor > 1:
                        img = img.subsample(factor, factor)
                    self.logo_img = img
                elif logo_path.lower().endswith(('.jpg', '.jpeg')):
                    if not PIL_AVAILABLE:
                        raise ImportError('Pillow (PIL) is required for JPG logos. Install with: pip install pillow')
                    pil_img = Image.open(logo_path)
                    pil_img = pil_img.convert('RGBA')
                    pil_img.thumbnail((128, 128), Image.LANCZOS)
                    self.logo_img = ImageTk.PhotoImage(pil_img)
                logo_label = ttk.Label(main_frame, image=self.logo_img, background='#f6fafd')
                logo_label.pack(pady=(24, 0))
            except Exception as e:
                messagebox.showerror('Logo Error', f'Could not load logo: {e}')

        # Title
        title = ttk.Label(main_frame, text='Student Welfare Fee Manager - מנהל רווחה לסטודנטים', style='Header.TLabel', anchor='center', justify='center')
        title.pack(fill='x', pady=(10, 0))

        # Frame for master list
        frame_master = ttk.Labelframe(main_frame, text='רשימת משלמי רווחה (Master Welfare Payers List)', style='Section.TLabelframe', padding=15)
        frame_master.pack(fill='x', padx=20, pady=(20, 10))

        self.lbl_payers_count = ttk.Label(frame_master, text='', anchor='e', justify='right')
        self.lbl_payers_count.pack(side='right', padx=10)

        btn_load_master = ttk.Button(frame_master, text='העלה/החלף קובץ משלמים...', command=self.load_master_list, width=25)
        btn_load_master.pack(side='right', padx=10)
        ToolTip(btn_load_master, 'Upload or replace the master list of welfare payers')

        # Frame for comparison
        frame_compare = ttk.Labelframe(main_frame, text='בדוק רשימת סטודנטים אחרת (Compare Another List)', style='Section.TLabelframe', padding=15)
        frame_compare.pack(fill='x', padx=20, pady=(0, 20))

        btn_compare = ttk.Button(frame_compare, text='העלה קובץ לבדיקה...', command=self.compare_new_list, width=25)
        btn_compare.pack(side='right', padx=10)
        ToolTip(btn_compare, 'Upload a student list to compare against the master list')

        # Results
        frame_results = ttk.Frame(main_frame, style='TFrame')
        frame_results.pack(fill='both', expand=True, padx=20, pady=10)

        # Payers
        lbl_in_payers = ttk.Label(frame_results, text='נמצאו ברשימת משלמים (Found in Payers List):', anchor='e', justify='right', font=('Arial', 13, 'bold'))
        lbl_in_payers.grid(row=0, column=1, sticky='e', pady=(0, 5))
        self.tree_in_payers = ttk.Treeview(frame_results, columns=('ID', 'Name', 'Email'), show='headings', height=12, style='Treeview')
        self.tree_in_payers.heading('ID', text='ת.ז. (ID)')
        self.tree_in_payers.heading('Name', text='שם (Name)')
        self.tree_in_payers.heading('Email', text='אימייל (Email)')
        self.tree_in_payers.grid(row=1, column=1, sticky='nsew', padx=(10,0))
        btn_export_in = ttk.Button(frame_results, text='ייצא CSV', command=lambda: self.export_list(self.in_payers, True), width=18)
        btn_export_in.grid(row=2, column=1, pady=8)
        ToolTip(btn_export_in, 'Export the list of payers to a CSV file')

        # Non-payers
        lbl_not_in_payers = ttk.Label(frame_results, text='לא נמצאו ברשימת משלמים (Not in Payers List):', anchor='e', justify='right', font=('Arial', 13, 'bold'))
        lbl_not_in_payers.grid(row=0, column=0, sticky='e', pady=(0, 5))
        self.tree_not_in_payers = ttk.Treeview(frame_results, columns=('ID', 'Name', 'Email'), show='headings', height=12, style='Treeview')
        self.tree_not_in_payers.heading('ID', text='ת.ז. (ID)')
        self.tree_not_in_payers.heading('Name', text='שם (Name)')
        self.tree_not_in_payers.heading('Email', text='אימייל (Email)')
        self.tree_not_in_payers.grid(row=1, column=0, sticky='nsew', padx=(0,10))
        btn_export_not_in = ttk.Button(frame_results, text='ייצא CSV', command=lambda: self.export_list(self.not_in_payers, False), width=18)
        btn_export_not_in.grid(row=2, column=0, pady=8)
        ToolTip(btn_export_not_in, 'Export the list of non-payers to a CSV file')

        # Configure grid weights
        frame_results.columnconfigure(0, weight=1)
        frame_results.columnconfigure(1, weight=1)
        frame_results.rowconfigure(1, weight=1)

    def refresh_payers_count(self):
        self.lbl_payers_count.config(text=f'מספר משלמים: {len(self.payers)}')

    def load_master_list(self):
        file_path = filedialog.askopenfilename(
            title='בחר קובץ משלמים (Select Welfare Payers CSV)',
            filetypes=[('CSV Files', '*.csv')]
        )
        if not file_path:
            return
        try:
            # Read header to let user select columns
            with open(file_path, newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.reader(csvfile)
                header = next(reader, None)
            if not header:
                messagebox.showerror('שגיאה', 'הקובץ ריק או לא תקין. (File is empty or invalid)')
                return
            id_col, name_col, email_col = self.ask_columns_selection(header, is_master=True)
            if not id_col:
                return  # User cancelled
            students = extract_students_from_csv(file_path, id_col, name_col, email_col)
            if not students:
                messagebox.showwarning('שגיאה', 'לא נמצאו ת.ז. חוקיות בקובץ. (No valid IDs found in file)')
                return
            self.payers = students
            save_payers_list(self.payers)
            self.refresh_payers_count()
            messagebox.showinfo('הצלחה', 'רשימת המשלמים עודכנה בהצלחה! (Welfare payers list updated)')
        except Exception as e:
            messagebox.showerror('שגיאה', f'שגיאה בקריאת הקובץ: {e}')

    def compare_new_list(self):
        if not self.payers:
            messagebox.showwarning('שגיאה', 'יש להעלות קודם רשימת משלמים. (Please load the welfare payers list first)')
            return
        file_path = filedialog.askopenfilename(
            title='בחר קובץ לבדיקה (Select Student List CSV)',
            filetypes=[('CSV Files', '*.csv')]
        )
        if not file_path:
            return
        try:
            # Read header to let user select columns
            with open(file_path, newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.reader(csvfile)
                header = next(reader, None)
            if not header:
                messagebox.showerror('שגיאה', 'הקובץ ריק או לא תקין. (File is empty or invalid)')
                return
            id_col, name_col, email_col = self.ask_columns_selection(header, is_master=False)
            if not id_col:
                return  # User cancelled
            students = extract_students_from_csv(file_path, id_col, name_col, email_col)
            in_payers, not_in_payers = compare_students(self.payers, students)
            self.in_payers = in_payers
            self.not_in_payers = not_in_payers
            self.update_results()
            messagebox.showinfo('הצלחה', f'נמצאו {len(in_payers)} משלמים ו-{len(not_in_payers)} לא משלמים.')
        except Exception as e:
            messagebox.showerror('שגיאה', f'שגיאה בקריאת הקובץ: {e}')

    def update_results(self):
        # Update payers
        self.tree_in_payers.delete(*self.tree_in_payers.get_children())
        for s in self.in_payers:
            self.tree_in_payers.insert('', 'end', values=(s.get('id', ''), s.get('name', ''), s.get('email', '')))
        # Update non-payers
        self.tree_not_in_payers.delete(*self.tree_not_in_payers.get_children())
        for s in self.not_in_payers:
            self.tree_not_in_payers.insert('', 'end', values=(s.get('id', ''), s.get('name', ''), s.get('email', '')))

    def export_list(self, students, is_payers):
        if not students:
            messagebox.showwarning('שגיאה', 'אין נתונים לייצא. (No data to export)')
            return
        file_path = filedialog.asksaveasfilename(
            title='שמור קובץ CSV',
            defaultextension='.csv',
            filetypes=[('CSV Files', '*.csv')],
            initialfile=('משלמים.csv' if is_payers else 'לא_משלמים.csv')
        )
        if not file_path:
            return
        try:
            export_students_to_csv(students, file_path)
            messagebox.showinfo('הצלחה', 'הקובץ נשמר בהצלחה! (File saved successfully)')
        except Exception as e:
            messagebox.showerror('שגיאה', f'שגיאה בשמירת הקובץ: {e}')

    def ask_columns_selection(self, header, is_master=False):
        # Dialog to select columns for ID, Name, Email
        dialog = tk.Toplevel(self.root)
        dialog.title('בחר עמודות (Select Columns)')
        dialog.geometry('400x320')  # Increased height for better layout
        dialog.grab_set()
        tk.Label(dialog, text='בחר את שם העמודה שמכילה את תעודת הזהות:', anchor='e', justify='right').pack(pady=(15,5))
        var_id = tk.StringVar(dialog)
        var_id.set(header[0])
        combo_id = ttk.Combobox(dialog, textvariable=var_id, values=header, state='readonly', width=30)
        combo_id.pack(pady=5)
        tk.Label(dialog, text='בחר את שם העמודה שמכילה את השם:', anchor='e', justify='right').pack(pady=(15,5))
        var_name = tk.StringVar(dialog)
        var_name.set(header[1] if len(header) > 1 else header[0])
        combo_name = ttk.Combobox(dialog, textvariable=var_name, values=header, state='readonly', width=30)
        combo_name.pack(pady=5)
        tk.Label(dialog, text='בחר את שם העמודה שמכילה את האימייל:', anchor='e', justify='right').pack(pady=(15,5))
        var_email = tk.StringVar(dialog)
        var_email.set(header[2] if len(header) > 2 else header[0])
        combo_email = ttk.Combobox(dialog, textvariable=var_email, values=header, state='readonly', width=30)
        combo_email.pack(pady=5)
        result = {'id': None, 'name': None, 'email': None}
        def on_ok():
            result['id'] = var_id.get()
            result['name'] = var_name.get()
            result['email'] = var_email.get()
            dialog.destroy()
        btn = tk.Button(dialog, text='אישור', command=on_ok, width=12)
        btn.pack(pady=(20, 15), side='bottom')
        dialog.wait_window()
        return result['id'], result['name'], result['email']

# --- Main Entrypoint ---
def main():
    root = tk.Tk()
    app = WelfareFeeApp(root)
    root.mainloop()

if __name__ == '__main__':
    main() 