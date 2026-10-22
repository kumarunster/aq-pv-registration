"""Pydantic-Modelle fuer Firmen, Kunden und Anlagen.

Stand: v0.2.0 - Datenmodell nach Kolya-Spezifikation (19.10.2026).
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Anlagetyp(str, Enum):
    PV = "pv"
    WALLBOX = "wallbox"
    WAERMEPUMPE = "waermepumpe"


# ---------------------------------------------------------------- Firmen

class CompanyCreate(BaseModel):
    """Firmen-Stammdaten (wiederkehrender Abschnitt)."""
    name: str
    address_street: str
    address_plz: str
    address_city: str
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    signature_url: Optional[str] = None
    installer_id: Optional[str] = None
    installer_origin_vnb: Optional[str] = None
    active: bool = True


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    address_street: Optional[str] = None
    address_plz: Optional[str] = None
    address_city: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    signature_url: Optional[str] = None
    installer_id: Optional[str] = None
    installer_origin_vnb: Optional[str] = None
    active: Optional[bool] = None


# ---------------------------------------------------------------- Kunde

class CustomerCreate(BaseModel):
    firstname: str
    lastname: str
    address_street: str
    address_plz: str
    address_city: str
    phone: Optional[str] = None
    email: Optional[str] = None
    iban: Optional[str] = None


class CustomerUpdate(BaseModel):
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    address_street: Optional[str] = None
    address_plz: Optional[str] = None
    address_city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    iban: Optional[str] = None


# ---------------------------------------------------------------- Anlage

class PanelInfo(BaseModel):
    """PV-Module (eine Gruppe)."""
    manufacturer: str
    type: str
    count: int
    kwp: str = "0"


class InverterInfo(BaseModel):
    """Einzelner Wechselrichter."""
    manufacturer: str
    type: str
    kw: str = "0"
    zerez_id: Optional[str] = None


class BatteryInfo(BaseModel):
    """Speicher (optional)."""
    manufacturer: str
    type: str
    kwh: str = "0"


class PlantCreate(BaseModel):
    """Anlage eines Kunden.

    Anlagetyp: PV, Wallbox oder Waermepumpe.
    Die meisten Felder sind anlagetyp-spezifisch:
      - PV: panels, inverters, battery, mstr, kw, kwh
      - Wallbox: inverters (Ladeleistung), kw
      - Waermepumpe: battery (Pufferspeicher), kw, kwh
    """
    anlagetyp: Anlagetyp
    company_id: str
    commission_date: Optional[date] = None
    kwp: Optional[str] = None
    kw: Optional[str] = None
    kwh: Optional[str] = None
    panels: Optional[PanelInfo] = None
    inverters: list[InverterInfo] = []
    battery: Optional[BatteryInfo] = None
    mstr_see_plant: Optional[str] = None
    mstr_eeg: Optional[str] = None
    mstr_see_battery: Optional[str] = None
    notes: Optional[str] = None


class PlantUpdate(BaseModel):
    anlagetyp: Optional[Anlagetyp] = None
    company_id: Optional[str] = None
    commission_date: Optional[date] = None
    kwp: Optional[str] = None
    kw: Optional[str] = None
    kwh: Optional[str] = None
    panels: Optional[PanelInfo] = None
    inverters: Optional[list[InverterInfo]] = None
    battery: Optional[BatteryInfo] = None
    mstr_see_plant: Optional[str] = None
    mstr_eeg: Optional[str] = None
    mstr_see_battery: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------- Health

class HealthResponse(BaseModel):
    status: str
    database: str
    version: str
    env: str
