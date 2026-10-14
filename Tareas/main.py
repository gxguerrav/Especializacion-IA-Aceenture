import json
#Crear Json
 
respuesta_json = '{"texto": "Hola, soy una respuesta generada", "detalles": {"modelo": "nombre-del-modelo", "tokens": 12}}'
print(type(respuesta_json))

respuesta_dict = json.loads(respuesta_json)
print(type(respuesta_dict))


print(respuesta_dict["texto"])
print(respuesta_dict["detalles"]["modelo"])