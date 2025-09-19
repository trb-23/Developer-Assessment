import tkinter as tk
from tkinter import ttk
import sqlite3 as sql
from logging import getLogger, DEBUG, Formatter, StreamHandler
from datetime import datetime
import random
import string
from tkcalendar import DateEntry
from sys import exit

logger = getLogger(__name__)
logger.setLevel(DEBUG)
formatter = Formatter(
    fmt='%(asctime)s - %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler = StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

DB = "database.db"

def CREATE_DEFAULT_TABLES() -> None:
    '''
    Creates the following tables and indexes if they do not exist already:

    Table: Customers:
        account     CHAR(15) PRIMARY KEY
        name        VARCHAR(30)
        balance     DOUBLE

    Table: Transactions:
        number      INTEGER PRIMARY KEY AUTOINCREMENT
        account     CHAR(15)
        date        DATETIME
        amount      DOUBLE
        DC          CHAR(1) CHECK(DC IN ('D', 'C'))
        FOREIGN KEY (account) REFERENCES Customers(account)
    '''
    query_customers = '''
        CREATE TABLE IF NOT EXISTS Customers (
            account CHAR(15) PRIMARY KEY,
            name VARCHAR(30),
            balance DOUBLE
        )
    '''
    query_transactions = '''
        CREATE TABLE IF NOT EXISTS Transactions (
            number INTEGER PRIMARY KEY AUTOINCREMENT,
            account CHAR(15),
            date DATETIME,
            amount DOUBLE,
            DC CHAR(1) CHECK(DC IN ('D', 'C')),
            FOREIGN KEY (account) REFERENCES Customers(account)
        )
    '''
    with sql.connect(DB) as db_connection:
        db_cursor = db_connection.cursor()
        try:
            db_cursor.execute(query_customers)
            logger.debug("'Customers' table successfully created/connected")
            db_cursor.execute('CREATE INDEX IF NOT EXISTS idx_customers_account ON Customers(account)')
            db_cursor.execute('CREATE INDEX IF NOT EXISTS idx_customers_name ON Customers(name)')

            db_cursor.execute(query_transactions)
            logger.debug("'Transactions' table successfully created/connected")
            db_cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_number ON Transactions(number)')
            db_cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_account ON Transactions(account)')

            db_connection.commit()
        except sql.Error as e:
            logger.error(f"Default tables creation failed: {e}")
            exit(1)

def validate_customer_name(name:str) -> None:
    '''
    Validates that customer name is of type VARCHAR(30).

    Args:
        name(str): Customer name to validate.

    Raises:
        TypeError: If name is not a string.
        ValueError: If name exceeds 30 characters.
    '''
    if not isinstance(name, str):
        raise TypeError(f"{name} is not a valid string.")
    if len(name) > 30:
        raise ValueError(f"Name cannot exceed 30 characters. Name is {len(name)} characters.")
    
def validate_amount(amount:float) -> None:
    '''
    Validates that balance is of type DOUBLE.

    Args:
        amount(float): Balance to validate.

    Raises:
        TypeError: If amount is not a valid float.
    '''
    try:
        balance_value = float(amount)
    except (TypeError, ValueError):
        raise TypeError(f"{amount} is not a valid float.")

def add_customer(name:str, balance:float = 0.0) -> None:
    '''
    Adds customer.

    Args:
        name(str): Name of the customer
        balance(float, optional): Initial balance of the customer account
    '''
    try:
        validate_customer_name(name)
    except TypeError as e:
        logger.error(e)
        return
    except ValueError as e:
        logger.error(e)
        return
    try:
        validate_amount(balance)
    except TypeError as e:
        logger.error(e)
        return

    account = generate_random_account_number()
    while True:
        if account_exists(account):
            account = generate_random_account_number()
            logger.debug("Duplicate hit, generating new account number.")
        else:
            break

    values = (account, name, balance)
    query = '''
        INSERT INTO Customers (account, name, balance)
        VALUES (?, ?, ?)
    '''
    with sql.connect(DB) as db_connection:
        db_cursor = db_connection.cursor()
        try:
            db_cursor.execute(query, values)
            logger.info(f"Added {name}, account number: {account}, balance = {balance}")
            db_connection.commit()
        except sql.Error as e:
            db_connection.rollback()
            logger.error(f"Failed to add account {account}: {e}")

def update_customer(account:str, new_name:str) -> None:
    '''
    Update customer name.

    Args:
        account(str): Account number of customer to update.
        new_name(str): Updated name corresponding to account number.
    '''
    try:
        validate_customer_name(new_name)
    except TypeError as e:
        logger.error(e)
        return
    except ValueError as e:
        logger.error(e)
        return
    
    values = (new_name, account)
    query = f"UPDATE Customers SET name = ? WHERE account = ?"
    with sql.connect(DB) as db_connection:
        db_cursor = db_connection.cursor()
        try:
            db_cursor.execute(query, values)
            logger.info(f"Account {account} name updated to {new_name}")
            db_connection.commit()
        except sql.Error as e:
            db_connection.rollback()
            logger.error(f"Failed to update account {account}: {e}")

def delete_customer(account:str) -> None:
    '''
    Delete customer.

    Args:
        account(str): Account number of customer to be deleted.
    '''
    values = (account, )
    query = '''
        DELETE FROM Customers WHERE account = ?
    '''
    with sql.connect(DB) as db_connection:
        db_cursor = db_connection.cursor()
        try:
            db_cursor.execute(query, values)
            logger.info(f"Account {account} deleted")
            db_connection.commit()
        except sql.Error as e:
            db_connection.rollback()
            logger.error(f"Failed to delete account {account}: {e}")

def transact(account:str, date:datetime.date, amount:float, DC:str = "D") -> None:
    '''
    Add transaction.

    Args:
        account(str): Account number to debit/credit.
        date(datetime.date): Date of the transaction.
        amount(float): Amount to debit/credit.
        DC(str): Indicates debit('D') or credit('C').
    '''
    try:
        validate_amount(amount)
    except TypeError as e:
        logger.error(e)
        return
    
    with sql.connect(DB) as db_connection:
        db_cursor = db_connection.cursor()
        try:
            values = (amount, account)
            operator = "+" if DC == "D" else "-"
            query = f'''
                UPDATE Customers SET balance = balance {operator} ? WHERE account = ?
            '''
            db_cursor.execute(query, values)
            operator_string = "debited from" if DC == "D" else "credited to"
            logger.info(f"{amount} {operator_string} {account}")

            values = (account, date, amount, DC)
            query = '''
                INSERT INTO Transactions (account, date, amount, DC)
                VALUES (?, ?, ?, ?)
            '''
            db_cursor.execute(query, values)
            logger.debug(f"{amount} {operator_string} {account} transaction saved")

            db_connection.commit()
        except sql.Error as e:
            db_connection.rollback()
            logger.error(f"Failed to load transaction: {e}")

def display_customers(*args) -> None:
    '''
    Refresh customer display portal.

    The 'Search:' entry and 'Sort:' comboboxes are taken into account for the refresh.
    '''
    for row in customer_tree.get_children():
        customer_tree.delete(row)

    reverse = False

    search_term = customer_search_input_var.get()
    search_string = "WHERE name LIKE ? OR account LIKE ?" if search_term else ""

    sort_from = customer_sort_from_combobox.get()
    match sort_from:
        case "Low - High":
            sort_from_string = "ASC"
        case "High - Low":
            sort_from_string = "DESC"
        case _:
            sort_from_string = ""

    sort_by = customer_sort_by_combobox.get()
    match sort_by:
        case "Default":
            sort_string = ""
            if sort_from_string == "DESC": reverse = True
        case "Account":
            sort_string = f"ORDER BY account {sort_from_string}"
        case "Name":
            sort_string = f"ORDER BY name {sort_from_string}"
        case "Balance":
            sort_string = f"ORDER BY balance {sort_from_string}"
        case _:
            sort_string = ""

    query = f"SELECT * FROM Customers"
    if search_string:
        query = query + " " + search_string
    if sort_string:
        query = query + " " + sort_string

    with sql.connect(DB) as db_connection:
        db_cursor = db_connection.cursor()
        if search_string:
            db_cursor.execute(query, ('%' + search_term + '%', '%' + search_term + '%'))
        else:
            db_cursor.execute(query)

    customer_columns = [description[0] for description in db_cursor.description]
    customer_tree["columns"] = customer_columns
    for col in customer_columns:
        customer_tree.heading(col, text=col)
        customer_tree.column(col, width=100)

    rows = db_cursor.fetchall()
    if reverse:
        rows.reverse()
    for row in rows:
        customer_tree.insert("", tk.END, values=row)

def display_transactions(*args) -> None:
    '''
    Refresh transactions display portal.

    The 'Search:' entry and 'Sort:' comboboxes are taken into account for the refresh.
    '''
    for row in transaction_tree.get_children():
        transaction_tree.delete(row)

    search_term = transaction_search_input_var.get()
    search_string = "WHERE number LIKE ? OR account LIKE ? OR date LIKE ?" if search_term else ""

    sort_from = transaction_sort_from_combobox.get()
    match sort_from:
        case "Low - High":
            sort_from_string = "ASC"
        case "High - Low":
            sort_from_string = "DESC"
        case _:
            sort_from_string = ""

    sort_by = transaction_sort_by_combobox.get()
    match sort_by:
        case "Number":
            sort_string = f"ORDER BY number {sort_from_string}"
        case "Account":
            sort_string = f"ORDER BY account {sort_from_string}"
        case "Date":
            sort_string = f"ORDER BY date {sort_from_string}"
        case "Amount":
            sort_string = f"ORDER BY amount {sort_from_string}"
        case _:
            sort_string = ""

    query = f"SELECT * FROM Transactions"
    if search_string:
        query = query + " " + search_string
    if sort_string:
        query = query + " " + sort_string

    with sql.connect(DB) as db_connection:
        db_cursor = db_connection.cursor()
        if search_string:
            db_cursor.execute(query, ('%' + search_term + '%', '%' + search_term + '%', '%' + search_term + '%'))
        else:
            db_cursor.execute(query)

    transaction_columns = [description[0] for description in db_cursor.description]
    transaction_tree["columns"] = transaction_columns
    for col in transaction_columns:
        transaction_tree.heading(col, text=col)
        transaction_tree.column(col, width=100)

    rows = db_cursor.fetchall()
    for row in rows:
        transaction_tree.insert("", tk.END, values=row)

def generate_random_account_number() -> str:
    '''
    Generate a random 15-character alphanumeric account number.

    Returns:
        str: Generated account number.
    '''
    characters = string.ascii_uppercase + string.digits
    account_number = ''.join(random.choices(characters, k=15))
    return account_number

def account_exists(account:str) -> bool:
    '''
    Checks if account exists in Customers database.

    Args:
        account(str): Account number to check.

    Returns:
        bool: True if account exists, False otherwise.
    '''
    with sql.connect(DB) as db_connection:
        db_cursor = db_connection.cursor()
        db_cursor.execute("SELECT 1 FROM Customers WHERE account = ?", (account, ))
        return db_cursor.fetchone() is not None

def new_customer_popup() -> None:
    '''
    Generates the 'Add New Customer' popup window.
    '''
    popup = tk.Toplevel(root)
    popup.title("Add New Customer")
    popup.geometry("600x400")
    popup.transient(root)
    popup.grab_set()

    def on_close():
        popup.grab_release()
        popup.destroy()
    popup.protocol("WM_DELETE_WINDOW", on_close)

    def add_customer_command(*args):
        new_name = new_customer_name_entry.get()
        add_customer(new_name)
        new_customer_name_entry.delete(0, tk.END)
        new_customer_name_entry.focus_set()
        display_customers()

    new_customer_name_label = ttk.Label(popup, text="New Customer Name:")
    new_customer_name_entry = ttk.Entry(popup)
    new_customer_name_entry.bind("<Return>", add_customer_command)
    new_customer_button = ttk.Button(popup, text="Add New Customer", command=add_customer_command)

    new_customer_name_label.pack(pady=10)
    new_customer_name_entry.pack(pady=20)
    new_customer_button.pack()

    new_customer_name_entry.focus_set()
    popup.wait_window()

def edit_customer_popup() -> None:
    '''
    Generates the 'Edit Customer' popup window.
    '''
    popup = tk.Toplevel(root)
    popup.title("Edit Customer")
    popup.geometry("600x400")
    popup.transient(root)
    popup.grab_set()

    def on_close():
        popup.grab_release()
        popup.destroy()
    popup.protocol("WM_DELETE_WINDOW", on_close)

    account_values = tk.StringVar(value=[])

    def edit_customer_command():
        update_customer(edit_customer_search_entry.get(), edit_customer_new_name_entry.get())
        display_customers()
        edit_customer_search_entry.delete(0, tk.END)
        edit_customer_new_name_entry.delete(0, tk.END)

    def on_entry_text_change(*args):
        search_term = edit_customer_search_var.get()
        if not search_term:
            account_values.set([])
            return
        
        query = '''
            SELECT * FROM Customers WHERE account LIKE ? OR name LIKE ?
        '''
        with sql.connect(DB) as db_connection:
            db_cursor = db_connection.cursor()
            db_cursor.execute(query, ('%' + search_term + '%', '%' + search_term + '%'))
        rows = db_cursor.fetchall()
        account_values.set([f"{row[1]} - {row[0]}" for row in rows])

    def on_listbox_select(event):
        widget = event.widget
        selected = widget.curselection()

        if selected:
            index = selected[0]
            value = widget.get(index)
            parsed_value = value.split(" - ")

            edit_customer_search_var.set(parsed_value[1])

    edit_customer_search_label = ttk.Label(popup, text="Search Account/Name to edit:")
    edit_customer_search_var = tk.StringVar(popup, value="")
    edit_customer_search_entry = ttk.Entry(popup, textvariable=edit_customer_search_var)
    edit_customer_search_var.trace_add("write", on_entry_text_change)
    edit_customer_search_listbox = tk.Listbox(popup, listvariable=account_values, justify="center")
    edit_customer_search_listbox.bind("<<ListboxSelect>>", on_listbox_select)
    edit_customer_new_name_label = ttk.Label(popup, text="New name:")
    edit_customer_new_name_entry = ttk.Entry(popup)
    edit_customer_button = ttk.Button(popup, text="Edit customer details", command=edit_customer_command)

    edit_customer_search_label.pack()
    edit_customer_search_entry.pack(pady=10)
    edit_customer_search_listbox.pack(fill="x")
    edit_customer_new_name_label.pack(pady=10)
    edit_customer_new_name_entry.pack()
    edit_customer_button.pack(pady=10)

    popup.wait_window()

def delete_customer_popup() -> None:
    '''
    Generates the 'Delete Customer' popup window.
    '''
    popup = tk.Toplevel(root)
    popup.title("Delete Customer")
    popup.geometry("600x400")
    popup.transient(root)
    popup.grab_set()

    def on_close():
        popup.grab_release()
        popup.destroy()
    popup.protocol("WM_DELETE_WINDOW", on_close)

    account_values = tk.StringVar(value=[])

    def delete_customer_command():
        delete_customer(delete_customer_search_entry.get())
        display_customers()
        delete_customer_search_entry.delete(0, tk.END)

    def on_entry_text_change(*args):
        search_term = delete_customer_search_var.get()
        if not search_term:
            account_values.set([])
            return
        
        query = '''
            SELECT * FROM Customers WHERE account LIKE ? OR name LIKE ?
        '''
        with sql.connect(DB) as db_connection:
            db_cursor = db_connection.cursor()
            db_cursor.execute(query, ('%' + search_term + '%', '%' + search_term + '%'))
        rows = db_cursor.fetchall()
        account_values.set([f"{row[1]} - {row[0]}" for row in rows])

    def on_listbox_select(event):
        widget = event.widget
        selected = widget.curselection()

        if selected:
            index = selected[0]
            value = widget.get(index)
            parsed_value = value.split(" - ")

            delete_customer_search_var.set(parsed_value[1])

    delete_customer_search_label = ttk.Label(popup, text="Search Account/Name to delete:")
    delete_customer_search_var = tk.StringVar(popup, value="")
    delete_customer_search_entry = ttk.Entry(popup, textvariable=delete_customer_search_var)
    delete_customer_search_var.trace_add("write", on_entry_text_change)
    delete_customer_search_listbox = tk.Listbox(popup, listvariable=account_values, justify="center")
    delete_customer_search_listbox.bind("<<ListboxSelect>>", on_listbox_select)
    delete_customer_button = ttk.Button(popup, text="Delete customer", command=delete_customer_command)

    delete_customer_search_label.pack()
    delete_customer_search_entry.pack(pady=10)
    delete_customer_search_listbox.pack(fill="x")
    delete_customer_button.pack(pady=10)

    popup.wait_window()

def new_transaction_popup() -> None:
    '''
    Generates the 'New Transaction' popup window.
    '''
    popup = tk.Toplevel(root)
    popup.title("New Transaction")
    popup.geometry("600x600")
    popup.transient(root)
    popup.grab_set()

    def on_close():
        popup.grab_release()
        popup.destroy()
    popup.protocol("WM_DELETE_WINDOW", on_close)

    account_values = tk.StringVar(value=[])

    def on_entry_text_change(*args):
        search_term = new_transaction_account_entry_var.get()

        if not search_term:
            account_values.set([])
            return
        
        query = '''
            SELECT * FROM Customers WHERE account LIKE ? OR name LIKE ?
        '''
        with sql.connect(DB) as db_connection:
            db_cursor = db_connection.cursor()
            db_cursor.execute(query, ('%' + search_term + '%', '%' + search_term + '%'))
        rows = db_cursor.fetchall()
        account_values.set([f"{row[1]} - {row[0]}" for row in rows])

    def on_listbox_select(event):
        widget = event.widget
        selected = widget.curselection()

        if selected:
            index = selected[0]
            value = widget.get(index)
            parsed_value = value.split(" - ")

            new_transaction_account_entry_var.set(parsed_value[1])

    def add_transaction_command():
        transact(new_transaction_account_entry_var.get(), new_transcation_date_entry.get_date(), new_transaction_amount_entry.get(), "D" if new_transaction_type_combobox.get() == "Debit" else "C")
        display_customers()
        display_transactions()

    new_transaction_date_label = ttk.Label(popup, text="New Transaction Date:")
    new_transcation_date_entry = DateEntry(popup)
    new_transaction_amount_label = ttk.Label(popup, text="Amount:")
    new_transaction_amount_entry = ttk.Entry(popup)
    new_transaction_type_combobox = ttk.Combobox(popup, values=["Debit", "Credit"], state="readonly")
    new_transaction_type_combobox.current(0)
    new_transaction_account_label = ttk.Label(popup, text="Search Account/Name:")
    new_transaction_account_entry_var = tk.StringVar(popup, "")
    new_transaction_account_entry = ttk.Entry(popup, textvariable=new_transaction_account_entry_var)
    new_transaction_account_entry_var.trace_add("write", on_entry_text_change)
    new_transaction_account_listbox = tk.Listbox(popup, listvariable=account_values, justify="center")
    new_transaction_account_listbox.bind('<<ListboxSelect>>', on_listbox_select)
    new_transaction_button = ttk.Button(popup, text="Add Transaction", command=add_transaction_command)

    new_transaction_date_label.pack(pady=10)
    new_transcation_date_entry.pack()
    new_transaction_amount_label.pack(pady=10)
    new_transaction_amount_entry.pack()
    new_transaction_type_combobox.pack(pady=10)
    new_transaction_account_label.pack()
    new_transaction_account_entry.pack()
    new_transaction_account_listbox.pack(pady=15, fill="x")
    new_transaction_button.pack()

    popup.wait_window()



CREATE_DEFAULT_TABLES()

root = tk.Tk()
root.title("Developer Assessment")
root.geometry("1000x1000")

menu_bar = tk.Menu(root)
root.config(menu=menu_bar)

customer_menu = tk.Menu(menu_bar, tearoff=0)
customer_menu.add_command(label="New", command=new_customer_popup)
customer_menu.add_command(label="Edit", command=edit_customer_popup)
customer_menu.add_separator()
customer_menu.add_command(label="Delete", command=delete_customer_popup)
menu_bar.add_cascade(label="Customer", menu=customer_menu)

transaction_menu = tk.Menu(menu_bar, tearoff=0)
transaction_menu.add_command(label="New", command=new_transaction_popup)
menu_bar.add_cascade(label="Transaction", menu=transaction_menu)

notebook = ttk.Notebook(root)
customer_pane = ttk.Frame(notebook)
transactions_pane = ttk.Frame(notebook)

notebook.add(customer_pane, text='Customers')
notebook.add(transactions_pane, text='Transactions')
notebook.pack(expand=True, fill='both')

customer_tree = ttk.Treeview(customer_pane, show="headings")
customer_tree_scollbar = ttk.Scrollbar(customer_pane, orient="vertical", command=customer_tree.yview)
customer_search_input_var = tk.StringVar(customer_pane, "")
customer_search_input_var.trace_add("write", display_customers)
customer_search_input = ttk.Entry(customer_pane, textvariable=customer_search_input_var)
customer_search_label = ttk.Label(customer_pane, text="Search:")
customer_sort_label = ttk.Label(customer_pane, text="Sort:")
customer_sort_by_combobox = ttk.Combobox(customer_pane, values=["Default", "Account", "Name", "Balance"], state="readonly")
customer_sort_by_combobox.current(0)
customer_sort_by_combobox.bind("<<ComboboxSelected>>", display_customers)
customer_sort_from_combobox = ttk.Combobox(customer_pane, values=["Low - High", "High - Low"], state="readonly")
customer_sort_from_combobox.current(0)
customer_sort_from_combobox.bind("<<ComboboxSelected>>", display_customers)

transaction_tree = ttk.Treeview(transactions_pane, show="headings")
transaction_tree_scrollbar = ttk.Scrollbar(transactions_pane, orient="vertical", command=transaction_tree.yview)
transaction_search_input_var = tk.StringVar(transactions_pane, "")
transaction_search_input_var.trace_add("write", display_transactions)
transaction_search_input = ttk.Entry(transactions_pane, textvariable=transaction_search_input_var)
transaction_search_label = ttk.Label(transactions_pane, text="Search:")
transaction_sort_label = ttk.Label(transactions_pane, text="Sort:")
transaction_sort_by_combobox = ttk.Combobox(transactions_pane, values=["Number", "Account", "Date", "Amount"], state="readonly")
transaction_sort_by_combobox.current(0)
transaction_sort_by_combobox.bind("<<ComboboxSelected>>", display_transactions)
transaction_sort_from_combobox = ttk.Combobox(transactions_pane, values=["Low - High", "High - Low"], state="readonly")
transaction_sort_from_combobox.current(1)
transaction_sort_from_combobox.bind("<<ComboboxSelected>>", display_transactions)

customer_search_label.pack()
customer_search_input.pack()
customer_sort_label.pack()
customer_sort_by_combobox.pack()
customer_sort_from_combobox.pack()
customer_tree.pack(expand=True, fill=tk.BOTH)
customer_tree_scollbar.pack(side="right", fill="y")

transaction_search_label.pack()
transaction_search_input.pack()
transaction_sort_label.pack()
transaction_sort_by_combobox.pack()
transaction_sort_from_combobox.pack()
transaction_tree.pack(expand=True, fill=tk.BOTH)
transaction_tree_scrollbar.pack(side="right", fill="y")

customer_tree.configure(yscrollcommand=customer_tree_scollbar.set)
transaction_tree.configure(yscrollcommand=transaction_tree_scrollbar.set)

display_customers()
display_transactions()

root.mainloop()