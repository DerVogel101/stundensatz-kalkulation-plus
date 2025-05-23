import sqlite3
import os
import locale
from typing import List, Dict, Tuple, Optional, Any

# Set locale for number formatting (German format)
try:
    locale.setlocale(locale.LC_ALL, 'de_DE')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'German')
    except:
        pass  # If locale setting fails, we'll use a custom formatting function

def format_number(number: float, decimal_places: int = 2) -> str:
    """
    Format a number with thousand separators and specified decimal places.

    Args:
        number (float): The number to format
        decimal_places (int): Number of decimal places to show

    Returns:
        str: Formatted number string with thousand separators
    """
    try:
        return locale.format_string(f'%.{decimal_places}f', number, grouping=True)
    except:
        # Fallback if locale formatting fails
        return f"{number:,.{decimal_places}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def init_db() -> None:
    """
    Initialize the SQLite database with the required table structure.
    """
    try:
        conn = sqlite3.connect('stundenlohn_scenarios.db')
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            worker_amount INTEGER NOT NULL,
            individual_costs REAL NOT NULL,
            overhead_costs REAL NOT NULL,
            hours REAL NOT NULL,
            earning_percentage REAL NOT NULL,
            vat_percentage REAL NOT NULL,
            selbstkostensatz REAL NOT NULL,
            netto REAL NOT NULL,
            brutto REAL NOT NULL,
            netto_selbstkosten_diff REAL NOT NULL,
            geld_fuer_chefchen REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        conn.commit()
    except Exception as e:
        print(f"Database initialization error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def save_scenario(name: str, worker_amount: int, individual_costs: float, 
                 overhead_costs: float, hours: float, earning_percentage: float, 
                 vat_percentage: float, description: str = "", chef: bool = False) -> int:
    """
    Save a scenario to the database.

    Args:
        name (str): Name of the scenario
        worker_amount (int): Number of employees
        individual_costs (float): Cost per employee
        overhead_costs (float): Overhead costs
        hours (float): Billable hours per employee
        earning_percentage (float): Profit margin as a decimal
        vat_percentage (float): VAT rate as a decimal
        description (str, optional): Description of the scenario. Defaults to "".

    Returns:
        int: ID of the saved scenario or -1 if an error occurred
    """
    try:
        selbstkostensatz, netto, brutto, netto_selbstkosten_diff, chef_kondensat = calc_hourwages(
            worker_amount, individual_costs, overhead_costs, 
            hours, earning_percentage, vat_percentage, geld_f_chefchen=chef
        )

        conn = sqlite3.connect('stundenlohn_scenarios.db')
        cursor = conn.cursor()

        cursor.execute('''
        INSERT INTO scenarios 
        (name, description, worker_amount, individual_costs, overhead_costs, hours, 
         earning_percentage, vat_percentage, selbstkostensatz, netto, brutto, netto_selbstkosten_diff, geld_fuer_chefchen)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, description, worker_amount, individual_costs, overhead_costs, hours, 
              earning_percentage, vat_percentage, selbstkostensatz, netto, brutto, netto_selbstkosten_diff, chef_kondensat))

        scenario_id = cursor.lastrowid
        conn.commit()
        return scenario_id
    except Exception as e:
        print(f"Error saving scenario: {e}")
        return -1
    finally:
        if 'conn' in locals():
            conn.close()

def get_all_scenarios() -> List[Dict[str, Any]]:
    """
    Retrieve all saved scenarios from the database.

    Returns:
        List[Dict[str, Any]]: List of dictionaries containing scenario data
    """
    try:
        conn = sqlite3.connect('stundenlohn_scenarios.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM scenarios ORDER BY created_at DESC')
        rows = cursor.fetchall()

        scenarios = [dict(row) for row in rows]
        return scenarios
    except Exception as e:
        print(f"Error retrieving scenarios: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def get_scenario(scenario_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific scenario by ID.

    Args:
        scenario_id (int): ID of the scenario to retrieve

    Returns:
        Optional[Dict[str, Any]]: Dictionary containing scenario data or None if not found
    """
    try:
        conn = sqlite3.connect('stundenlohn_scenarios.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM scenarios WHERE id = ?', (scenario_id,))
        row = cursor.fetchone()

        scenario = dict(row) if row else None
        return scenario
    except Exception as e:
        print(f"Error retrieving scenario {scenario_id}: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def delete_scenario(scenario_id: int) -> bool:
    """
    Delete a scenario from the database.

    Args:
        scenario_id (int): ID of the scenario to delete

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        conn = sqlite3.connect('stundenlohn_scenarios.db')
        cursor = conn.cursor()

        cursor.execute('DELETE FROM scenarios WHERE id = ?', (scenario_id,))
        success = cursor.rowcount > 0

        conn.commit()
        return success
    except Exception as e:
        print(f"Error deleting scenario {scenario_id}: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def calc_hourwages(worker_amount: int, individual_costs: float, overhead_costs: float, hours: float, earning_percentage: float, vat_percentage : float, geld_f_chefchen: bool) -> Tuple[float, float, float, float, float]:
    """
    Calculate hourly rates based on input parameters.

    Args:
        worker_amount (int): Number of employees
        individual_costs (float): Cost per employee
        overhead_costs (float): Overhead costs
        hours (float): Billable hours per employee
        earning_percentage (float): Profit margin as a decimal (e.g., 0.15 for 15%)
        vat_percentage (float): VAT rate as a decimal (e.g., 0.19 for 19%)
        geld_f_chefchen (bool): Flag to indicate if the calculation includes "Verdampfung"

    Returns:
        tuple: A tuple containing (self_cost_rate, net_rate, gross_rate, netto_selbstkosten_diff, chef_kondensat) rounded to 2 decimal places

    Raises:
        ValueError: If any input parameters are invalid (e.g., division by zero)
    """
    try:
        # Validate inputs
        if worker_amount <= 0:
            raise ValueError("Anzahl Mitarbeitende muss größer als 0 sein")
        if hours <= 0:
            raise ValueError("Fakturierbare Stunden müssen größer als 0 sein")

        gesamt_einzelkosten = worker_amount * individual_costs
        selbstkosten = gesamt_einzelkosten + overhead_costs
        verrechenbare_stunden = worker_amount * hours

        # Prevent division by zero
        if verrechenbare_stunden == 0:
            raise ValueError("Verrechenbare Stunden dürfen nicht 0 sein")

        selbstkostensatz = selbstkosten / verrechenbare_stunden
        netto = selbstkostensatz * (1 + earning_percentage)
        brutto = netto * (1 + vat_percentage)
        netto_selbstkosten_diff = netto - selbstkostensatz
        chef_kondensat = 0.0
        if geld_f_chefchen:
            chef_kondensat = netto_selbstkosten_diff * (0.6 * earning_percentage)
            netto_selbstkosten_diff -= chef_kondensat
            brutto -= chef_kondensat

        return round(selbstkostensatz, 2), round(netto, 2), round(brutto, 2), round(netto_selbstkosten_diff, 2), round(chef_kondensat, 2)
    except Exception as e:
        print(f"Calculation error: {e}")
        # Return default values in case of error
        return 0.0, 0.0, 0.0, 0.0, 0.0


if __name__ == '__main__':
    selbstkostensatz, netto, brutto, netto_selbstkosten_diff = calc_hourwages(8, 60000, 230000, 1512, 0.15, 0.19)
    print("Selbstkostensatz:", selbstkostensatz, "€ | Netto:", netto, "€ | Brutto:", brutto, "€ | Netto-Selbstkosten Diff.:", netto_selbstkosten_diff, "€")
