# Precios de ejemplo (CLP): reemplazar por los reales del negocio.
CATALOGO = (
    "Catálogo: cilindro de 5 kg $12.000, de 11 kg $20.000, "
    "de 15 kg $27.000, de 45 kg $75.000. Despacho a domicilio gratis."
)

BANCO_DE_PROMPTS = [
    {
        "nombre": "clasificar_intencion",
        "system_instruction": (
            "Eres el clasificador de mensajes de una empresa que vende gas en "
            "cilindros a domicilio. Responde únicamente con un objeto JSON "
            "válido, sin texto adicional y sin bloques de markdown, con las "
            "claves 'intencion' ('comprar', 'cotizar', 'consultar_pedido', "
            "'reclamo' u 'otro') y 'confianza' (número entre 0 y 1)."
        ),
        "ejemplo_usuario": "Hola, necesito dos balones de 15 kilos para hoy.",
        "claves_esperadas": ["intencion", "confianza"],
        "response_schema": {
            "type": "OBJECT",
            "properties": {
                "intencion": {"type": "STRING"},
                "confianza": {"type": "NUMBER"},
            },
            "required": ["intencion", "confianza"],
        },
    },
    {
        "nombre": "extraer_pedido",
        "system_instruction": (
            "Extraes los datos de un pedido de gas en cilindros. Responde "
            "únicamente con un objeto JSON válido, sin texto adicional y sin "
            "bloques de markdown, con las claves 'tipo_cilindro_kg' (entero: "
            "5, 11, 15 o 45; 0 si no se indica), 'cantidad' (entero; 0 si no "
            "se indica), 'direccion' (string; vacío si no se indica) y "
            "'datos_faltantes' (lista con los nombres de las claves anteriores "
            "que el cliente no informó)."
        ),
        "ejemplo_usuario": "Quiero 2 cilindros de 15 kilos, mi dirección es Av. Los Leones 1234, Providencia.",
        "claves_esperadas": ["tipo_cilindro_kg", "cantidad", "direccion", "datos_faltantes"],
        "response_schema": {
            "type": "OBJECT",
            "properties": {
                "tipo_cilindro_kg": {"type": "INTEGER"},
                "cantidad": {"type": "INTEGER"},
                "direccion": {"type": "STRING"},
                "datos_faltantes": {"type": "ARRAY", "items": {"type": "STRING"}},
            },
            "required": ["tipo_cilindro_kg", "cantidad", "direccion", "datos_faltantes"],
        },
    },
    {
        "nombre": "respuesta_de_venta",
        "system_instruction": (
            "Eres el asistente de ventas de una empresa de gas en cilindros. "
            "Atiendes de forma amable y breve, en español. " + CATALOGO + " "
            "Nunca inventes productos ni precios fuera del catálogo. Responde "
            "únicamente con un objeto JSON válido, sin texto adicional y sin "
            "bloques de markdown, con las claves 'mensaje' (respuesta al "
            "cliente, máximo 2 oraciones), 'total' (entero en pesos; 0 si aún "
            "no se puede calcular) y 'siguiente_paso' ('pedir_direccion', "
            "'confirmar_pedido', 'pedir_producto' u 'otro')."
        ),
        "ejemplo_usuario": "Quiero 2 cilindros de 15 kilos, mi dirección es Av. Los Leones 1234, Providencia.",
        "claves_esperadas": ["mensaje", "total", "siguiente_paso"],
        "response_schema": {
            "type": "OBJECT",
            "properties": {
                "mensaje": {"type": "STRING"},
                "total": {"type": "INTEGER"},
                "siguiente_paso": {"type": "STRING"},
            },
            "required": ["mensaje", "total", "siguiente_paso"],
        },
    },
]