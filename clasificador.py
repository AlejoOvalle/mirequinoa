# clasificador.py

CATEGORIAS_OFICIALES = {
    "1. Emergencias y Servicios Públicos": [
        "police", "fire_station", "hospital", "carabineros", "bomberos", 
        "cesfam", "posta", "ambulancia", "municipalidad", "apr", "registro civil"
    ],
    "11. Belleza y Cuidado Personal": [
        "beauty_salon", "hair_care", "spa", "barber", "hairdresser",
        "peluqueria", "barberia", "estetica", "manicure", "pedicure", 
        "salon de belleza", "unas", "pestanas", "depilacion"
    ],
    "2. Panadería, Almacén y Gastronomía": [
        "restaurant", "bakery", "cafe", "meal_takeaway", "supermarket",
        "panaderia", "amasanderia", "almacen", "minimarket", "botilleria", 
        "verduleria", "carniceria", "sushi", "pizzeria", "comida rapida", "restobar"
    ],
    "3. Campo, Agroindustria y Viveros": [
        "vivero", "plantas", "agricola", "agropecuaria", "riego", "semillas", 
        "packing", "exportadora", "fruticola", "campo"
    ],
    "4. Comercio Local, Bazar y Moda": [
        "clothing_store", "shoe_store", "shopping_mall", "bazar", "paqueteria", 
        "libreria", "regalos", "ropa", "boutique", "joyeria"
    ],
    "5. Arte, Artesanía y Creación Local": [
        "art_gallery", "artesania", "ceramica", "telar", "greda", "patrimonio"
    ],
    "6. Gasfitería, Electricidad y Hogar": [
        "gasfiter", "electricista", "climatizacion", "aire acondicionado", "estufa"
    ],
    "7. Construcción, Ferretería y Terminaciones": [
        "hardware_store", "ferreteria", "materiales", "aridos", "maderas", "cemento"
    ],
    "8. Oficios y Maestros Locales": [
        "carpintero", "soldador", "cerrajero", "tapicero", "costurera", "zapatero"
    ],
    "9. Mecánica, Automotriz y Transporte": [
        "car_repair", "gas_station", "taller mecanico", "vulcanizacion", 
        "lubricentro", "repuestos", "fletes", "radiotaxi"
    ],
    "10. Salud, Farmacia y Bienestar": [
        "pharmacy", "dentist", "doctor", "farmacia", "dental", "dentista", "clinica"
    ],
    "12. Servicios Profesionales, Negocios y TI": [
        "lawyer", "accounting", "contador", "abogado", "notaria", "informatica"
    ],
    "13. Deporte, Recreación y Turismo": [
        "gym", "park", "padel", "canchas", "gimnasio", "futbol", "piscina", "camping"
    ],
    "14. Bolsa de Empleo y Temporada": [
        "temporeros", "cuadrillas", "contratista", "cosecha", "empleo"
    ]
}

def categorizar_negocio(nombre: str, tipos_google: str = "", descripcion: str = "") -> str:
    texto = f"{nombre} {tipos_google} {descripcion}".lower()
    
    # 1. Belleza primero para que barberías no choquen con otras
    for p in CATEGORIAS_OFICIALES["11. Belleza y Cuidado Personal"]:
        if p in texto:
            return "11. Belleza y Cuidado Personal"
            
    # 2. Resto de categorías
    for cat, palabras in CATEGORIAS_OFICIALES.items():
        for p in palabras:
            if p in texto:
                return cat
                
    return "4. Comercio Local, Bazar y Moda"
