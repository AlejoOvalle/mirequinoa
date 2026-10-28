# clasificador.py

CATEGORIAS_OFICIALES = {
    "1. Emergencias y Servicios Públicos": [
        "police", "fire_station", "hospital", "local_government_office",
        "carabineros", "bomberos", "cesfam", "posta", "ambulancia", "municipalidad", 
        "registro civil", "apr", "agua potable", "cge", "seguridad ciudadana"
    ],
    "2. Panadería, Almacén y Gastronomía": [
        "restaurant", "bakery", "cafe", "meal_takeaway", "bar", "grocery_or_supermarket", "liquor_store",
        "panaderia", "amasanderia", "almacen", "minimarket", "botilleria", "supermercado",
        "verduleria", "carniceria", "rotiseria", "sushi", "pizzeria", "comida rapida", "pasteleria"
    ],
    "3. Campo, Agroindustria y Viveros": [
        "vivero", "plantas", "agricola", "agropecuaria", "riego", "semillas", "fertilizantes",
        "packing", "exportadora", "fruticola", "parron", "cerezas", "campo", "huerto", "agro"
    ],
    "4. Comercio Local, Bazar y Moda": [
        "clothing_store", "shoe_store", "shopping_mall", "home_goods_store",
        "bazar", "paqueteria", "libreria", "regalos", "ropa", "vestuario", "calzado",
        "boutique", "joyeria", "menaje", "jugueteria"
    ],
    "5. Arte, Artesanía y Creación Local": [
        "art_gallery", "museum", "artesania", "ceramica", "telar", "greda", "escultura",
        "cuadros", "patrimonio", "orfebreria", "taller de arte", "hecho a mano"
    ],
    "6. Gasfitería, Electricidad y Hogar": [
        "gasfiter", "plomeria", "electricista", "instalacion electrica", "climatizacion",
        "aire acondicionado", "estufa", "pellet", "fosas septicas", "paneles solares", "gas"
    ],
    "7. Construcción, Ferretería y Terminaciones": [
        "hardware_store", "ferreteria", "materiales", "aridos", "maderas", "cemento",
        "maestranza", "techumbres", "pinturas", "galpones", "hormigon", "albanileria"
    ],
    "8. Oficios y Maestros Locales": [
        "carpintero", "carpinteria", "soldador", "soldadura", "cerrajero", "cerrajeria",
        "tapicero", "tapiceria", "costurera", "modista", "zapatero", "vidrieria", "mueblista"
    ],
    "9. Mecánica, Automotriz y Transporte": [
        "car_repair", "car_wash", "gas_station",
        "taller mecanico", "vulcanizacion", "lubricentro", "repuestos", "desabolladura",
        "fletes", "mudanzas", "radiotaxi", "taxi", "grua", "transporte escolar"
    ],
    "10. Salud, Farmacia y Bienestar": [
        "pharmacy", "dentist", "doctor", "physiotherapist", "veterinary_care",
        "farmacia", "dental", "dentista", "clinica", "medico", "psicologo", "kinesiologo",
        "optica", "laboratorio", "veterinaria", "podologia", "masajes"
    ],
    "11. Belleza y Cuidado Personal": [
        "beauty_salon", "hair_care", "spa",
        "peluqueria", "barberia", "estetica", "manicure", "pedicure", "unhas",
        "pestanas", "depilacion", "skincare"
    ],
    "12. Servicios Profesionales, Negocios y TI": [
        "lawyer", "accounting", "real_estate_agency",
        "contador", "abogado", "asesoria", "notaria", "informatica", "servicio tecnico",
        "computadores", "publicidad", "diseno", "imprenta", "corretaje", "parcelas"
    ],
    "13. Deporte, Recreación y Turismo": [
        "gym", "campground", "park", "tourist_attraction",
        "padel", "canchas", "gimnasio", "futbol", "piscina", "camping", "turismo",
        "cabanas", "quincho", "eventos", "centro recreativo", "crossfit"
    ],
    "14. Bolsa de Empleo y Temporada": [
        "employment_agency", "temporeros", "cuadrillas", "contratista", "cosecha",
        "recursos humanos", "empleo", "ofertas laborales", "faena", "trabajadores"
    ]
}

def categorizar_negocio(nombre: str, tipos_google: str = "", descripcion: str = "") -> str:
    texto = f"{nombre} {tipos_google} {descripcion}".lower()
    for categoria, palabras in CATEGORIAS_OFICIALES.items():
        for p in palabras:
            if p in texto:
                return categoria
    return "4. Comercio Local, Bazar y Moda"