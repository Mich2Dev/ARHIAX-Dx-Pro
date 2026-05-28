export const COUNTRIES = [
  "Colombia", "México", "Argentina", "Chile", "Perú", "Ecuador",
  "Venezuela", "Brasil", "Bolivia", "Paraguay", "Uruguay",
  "Costa Rica", "Panamá", "Guatemala", "Honduras", "El Salvador",
  "Nicaragua", "República Dominicana", "Cuba", "España", "Estados Unidos",
  "Otro",
];

export const CITIES_BY_COUNTRY: Record<string, string[]> = {
  Colombia: [
    "Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena",
    "Cúcuta", "Bucaramanga", "Pereira", "Santa Marta", "Ibagué",
    "Manizales", "Pasto", "Neiva", "Villavicencio", "Armenia",
    "Valledupar", "Montería", "Sincelejo", "Popayán", "Tunja",
    "Florencia", "Quibdó", "Riohacha", "San Andrés", "Leticia",
    "Otra",
  ],
  México: [
    "Ciudad de México", "Guadalajara", "Monterrey", "Puebla", "Tijuana",
    "León", "Juárez", "Zapopan", "Mérida", "San Luis Potosí", "Otra",
  ],
  Argentina: [
    "Buenos Aires", "Córdoba", "Rosario", "Mendoza", "Tucumán",
    "La Plata", "Mar del Plata", "Salta", "Santa Fe", "Otra",
  ],
  Chile: [
    "Santiago", "Valparaíso", "Concepción", "La Serena", "Antofagasta",
    "Temuco", "Rancagua", "Talca", "Arica", "Otra",
  ],
  Perú: [
    "Lima", "Arequipa", "Trujillo", "Chiclayo", "Piura",
    "Iquitos", "Cusco", "Huancayo", "Otra",
  ],
};

export function getCities(country: string): string[] {
  return CITIES_BY_COUNTRY[country] ?? ["Otra"];
}
