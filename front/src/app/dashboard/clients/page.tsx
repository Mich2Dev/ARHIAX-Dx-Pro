/**
 * ═══════════════════════════════════════════════════════════════════════════
 * PÁGINA: Lista de Clientes
 * ═══════════════════════════════════════════════════════════════════════════
 * 
 * RUTA: http://localhost:3000/dashboard/clients
 * 
 * DESCRIPCIÓN:
 * Esta página muestra la lista de todos los clientes y sus diagnósticos.
 * 
 * RELACIONES:
 * ├─ Importa: ClientsView (componente que hace el trabajo pesado)
 * │   └─ Ubicación: src/components/features/clients/ClientsView.tsx
 * │   └─ Función: Muestra tabla de clientes, llama a la API, maneja filtros
 * 
 * CÓMO FUNCIONA:
 * 1. Esta página es solo un "contenedor" simple
 * 2. Delega todo el trabajo al componente ClientsView
 * 3. ClientsView se encarga de cargar datos, mostrar tabla, etc.
 * 
 * ANALOGÍA HTML:
 * Es como tener un archivo clients.html que incluye otro archivo con <iframe>
 * ═══════════════════════════════════════════════════════════════════════════
 */

// Importar el componente que hace todo el trabajo
import { ClientsView } from "@/components/features/clients/ClientsView";

// Función principal de la página
export default function ClientsPage() {
  // Simplemente devuelve el componente ClientsView
  return <ClientsView />;
}
