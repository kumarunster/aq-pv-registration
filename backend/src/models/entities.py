"""Pydantic-Modelle fuer Firmen, Kunden und Anlagen.

Stand: v0.3.1 - Lageplan + Dokumente an Anlage (28.10.2026).
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Anlagetyp(str, Enum):
    PV = "pv"
    WALLBOX = "wallbox"
    WAERMEPUMPE = "waermepumpe"


# ---------------------------------------------------------------- Lageplan

class LageplanDocument(BaseModel):
    """Lageplan-JSON (spiegelt backend/src/routers/lageplan/schemas.py::Layout).

    Wird als komplettes Layout-Objekt gespeichert (title, background,
    elements, metadata).
    """
    title: str = "Lageplan"
    background_image_url: Optional[str] = None
    background_image_width: Optional[float] = None
    background_image_height: Optional[float] = None
    elements: list[dict] = []
    metadata: dict = {}


class DocumentRef(BaseModel):
    """Referenz auf ein gespeichertes Dokument (z. B. PDF)."""
    name: str
    url: str
    content_type: str = "application/pdf"
    created_at: Optional[datetime] = None


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

    Adressdaten: die Anlage kann auf einem anderen Grundstueck stehen
    als der Kunde — daher eigene Adress-Felder (address_*).
    """
    anlagetyp: Anlagetyp
    company_id: Optional[str] = None
    commission_date: Optional[date] = None
    kwp: Optional[str] = None
    kw: Optional[str] = None
    kwh: Optional[str] = None
    # Anlage-Adresse: address_from_customer=true => Adresse kommt vom Kunden,
    # address_*-Felder bleiben leer. address_from_customer=false => eigene Adress-Felder.
    address_from_customer: bool = True
    address_street: Optional[str] = None
    address_plz: Optional[str] = None
    address_city: Optional[str] = None
    # Grundstueckdaten (separate Felder)
    gemarkung: Optional[str] = None
    flur: Optional[str] = None
    flurstueck: Optional[str] = None
    panels: Optional[PanelInfo] = None
    inverters: list[InverterInfo] = []
    battery: Optional[BatteryInfo] = None
    mstr_see_plant: Optional[str] = None
    mstr_eeg: Optional[str] = None
    mstr_see_battery: Optional[str] = None
    notes: Optional[str] = None
    # Status (Admin gesetzt: in_pruefung | angemeldet | abgeschlossen)
    status: Optional[str] = None
    lageplan: Optional[LageplanDocument] = None
    documents: list[DocumentRef] = []


class PlantUpdate(BaseModel):
    anlagetyp: Optional[Anlagetyp] = None
    company_id: Optional[str] = None
    commission_date: Optional[date] = None
    kwp: Optional[str] = None
    kw: Optional[str] = None
    kwh: Optional[str] = None
    # Anlage-Adresse
    address_from_customer: Optional[bool] = None
    address_street: Optional[str] = None
    address_plz: Optional[str] = None
    address_city: Optional[str] = None
    # Grundstueckdaten
    gemarkung: Optional[str] = None
    flur: Optional[str] = None
    flurstueck: Optional[str] = None
    panels: Optional[PanelInfo] = None
    inverters: Optional[list[InverterInfo]] = None
    battery: Optional[BatteryInfo] = None
    mstr_see_plant: Optional[str] = None
    mstr_eeg: Optional[str] = None
    mstr_see_battery: Optional[str] = None
    notes: Optional[str] = None
    lageplan: Optional[LageplanDocument] = None
    documents: Optional[list[DocumentRef]] = None


class CustomerCreate(BaseModel):
    firstname: str
    lastname: str
    address_street: str
    address_plz: str
    address_city: str
    phone: Optional[str] = None
    email: Optional[str] = None
    iban: Optional[str] = None
    plants: Optional[list["PlantCreate"]] = None


class CustomerUpdate(BaseModel):
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    address_street: Optional[str] = None
    address_plz: Optional[str] = None
    address_city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    iban: Optional[str] = None
    plants: Optional[list["PlantUpdate"]] = None



# ---------------------------------------------------------------- Health

class HealthResponse(BaseModel):
    status: str
    database: str
    version: str
    env: str
