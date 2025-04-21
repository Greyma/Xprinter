from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from escpos.printer import Usb
import logging
import usb.core
import usb.util

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation de FastAPI
app = FastAPI(title="Xprinter Generic Print API")

# Modèle pour les données de la requête
class PrintRequest(BaseModel):
    text: str
    bold: bool = False
    align: str = "left"  # left, center, right

# Fonction pour détecter automatiquement une imprimante Xprinter
def find_xprinter():
    known_xprinter_vids = [0x0483, 0x5740, 0x04B8]  # Ajoute ici les VendorID si nécessaire

    for dev in usb.core.find(find_all=True):
        try:
            
            print(f"ID Vendor: {hex(dev.idVendor)} | ID Product: {hex(dev.idProduct)} | Bus: {dev.bus} | Address: {dev.address}")
            if dev.idVendor in known_xprinter_vids or (dev.manufacturer and "Xprinter" in dev.manufacturer):
                logger.info(f"Détection: VendorID={hex(dev.idVendor)}, ProductID={hex(dev.idProduct)}")
                try:
                    return Usb(dev.idVendor, dev.idProduct, timeout=5000)
                except Exception as e:
                    logger.warning(f"Erreur de connexion USB à {hex(dev.idVendor)}:{hex(dev.idProduct)} - {e}")
        except Exception as e:
            logger.debug(f"Erreur lors de l'inspection du périphérique USB: {e}")
    return None

# End-point pour impression
@app.post("/print")
async def print_text(request: PrintRequest):
    printer = find_xprinter()  # RÉCUPÉRATION À CHAQUE REQUÊTE

    if printer is None:
        logger.error("Aucune imprimante détectée")
        raise HTTPException(status_code=500, detail="Imprimante Xprinter non détectée ou inaccessible")

    try:
        # Configuration alignement
        align = request.align.lower()
        if align in ["center", "right", "left"]:
            printer.set(align=align)
        else:
            printer.set(align="left")

        # Gras
        printer.set(bold=request.bold)

        # Impression texte
        safe_text = request.text.encode('utf-8', 'ignore').decode('ascii', 'ignore')
        printer.text(safe_text + "\n")

        # Tentative de coupe
        try:
            printer.cut()
        except Exception as e:
            logger.warning(f"Coupe non supportée : {e}")

        return {"message": "Impression réussie"}
    except Exception as e:
        logger.error(f"Erreur d'impression : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur d'impression : {str(e)}")

# End-point de vérification
@app.get("/health")
async def health_check():
    return {"status": "API is running"}
