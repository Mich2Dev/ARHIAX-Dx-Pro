# ARHIAX Dx Frontend

Frontend de la plataforma de diagnósticos organizacionales ARHIAX Dx v5.1

## 🏗️ Estructura del Proyecto

```
front/
├── public/                 # Assets estáticos (imágenes, fuentes, etc.)
├── src/
│   ├── app/               # Next.js App Router - Páginas y rutas
│   │   ├── dashboard/     # Dashboard principal
│   │   ├── login/         # Página de login
│   │   ├── survey/        # Encuestas públicas
│   │   ├── layout.tsx     # Layout raíz
│   │   └── page.tsx       # Página de inicio
│   │
│   ├── components/        # Componentes React
│   │   ├── features/      # Componentes por funcionalidad
│   │   │   ├── admin/     # Panel de administración
│   │   │   ├── clients/   # Gestión de clientes
│   │   │   ├── compliance/# Compliance y gobernanza
│   │   │   ├── dashboard/ # Dashboard components
│   │   │   ├── diagnostics/# Diagnósticos y pipeline
│   │   │   ├── ledger/    # Evidence ledger
│   │   │   ├── reviews/   # Revisiones humanas
│   │   │   └── survey/    # Sistema de encuestas
│   │   ├── layout/        # Componentes de layout (Header, Sidebar)
│   │   ├── providers/     # React Context Providers
│   │   ├── auth/          # Componentes de autenticación
│   │   └── ui/            # Componentes UI base reutilizables
│   │
│   ├── styles/            # Estilos CSS
│   │   ├── globals.css    # Estilos globales y Tailwind
│   │   └── themes/        # Temas personalizados
│   │
│   ├── lib/               # Librerías y utilidades
│   │   ├── api/           # Clientes API
│   │   │   ├── client.ts  # Cliente HTTP principal
│   │   │   ├── auth.ts    # API de autenticación
│   │   │   └── index.ts   # Exports
│   │   ├── hooks/         # Custom React Hooks
│   │   ├── types/         # TypeScript types y interfaces
│   │   │   └── index.ts   # Tipos compartidos
│   │   ├── utils/         # Funciones helper
│   │   │   ├── helpers.ts # Utilidades generales
│   │   │   ├── validation.ts # Validaciones
│   │   │   ├── geo.ts     # Utilidades geográficas
│   │   │   └── index.ts   # Exports
│   │   └── index.ts       # Export principal
│   │
│   ├── config/            # Configuración de la aplicación
│   │   ├── pipeline-presets.ts # Presets del pipeline
│   │   └── index.ts       # Configuración general
│   │
│   ├── context/           # React Context
│   │   └── AuthContext.tsx # Contexto de autenticación
│   │
│   ├── i18n/              # Internacionalización
│   │   └── request.ts     # Configuración i18n
│   │
│   └── messages/          # Traducciones
│       ├── es.json        # Español
│       └── en.json        # Inglés
│
├── .env.local             # Variables de entorno locales
├── package.json           # Dependencias
├── tsconfig.json          # Configuración TypeScript
├── tailwind.config.ts     # Configuración Tailwind CSS
├── next.config.js         # Configuración Next.js
└── Dockerfile             # Docker para producción
```

## 🚀 Tecnologías

- **Framework:** Next.js 14 (App Router)
- **Lenguaje:** TypeScript
- **Estilos:** Tailwind CSS
- **UI Components:** Radix UI
- **State Management:** React Context + Redux Toolkit
- **Forms:** React Hook Form
- **Charts:** Recharts
- **HTTP Client:** Axios
- **i18n:** next-intl

## 📦 Instalación

```bash
npm install
```

## 🔧 Desarrollo

```bash
npm run dev
```

Abre [http://localhost:3000](http://localhost:3000)

## 🏗️ Build

```bash
npm run build
npm start
```

## 🐳 Docker

```bash
docker build -t arhiax-dx-front .
docker run -p 3000:3000 arhiax-dx-front
```

## 📝 Convenciones de Código

### Estructura de Componentes

```typescript
// Imports
import { useState } from 'react';
import { Button } from '@/components/ui/Button';

// Types
interface MyComponentProps {
  title: string;
  onAction: () => void;
}

// Component
export function MyComponent({ title, onAction }: MyComponentProps) {
  const [state, setState] = useState(false);
  
  return (
    <div>
      <h1>{title}</h1>
      <Button onClick={onAction}>Action</Button>
    </div>
  );
}
```

### Imports

Usar alias `@/` para imports absolutos:

```typescript
// ✅ Correcto
import { api } from '@/lib/api';
import { Button } from '@/components/ui/Button';

// ❌ Evitar
import { api } from '../../../lib/api';
```

### Naming

- **Componentes:** PascalCase (`MyComponent.tsx`)
- **Hooks:** camelCase con prefijo `use` (`useAuth.ts`)
- **Utilidades:** camelCase (`formatDate.ts`)
- **Tipos:** PascalCase (`UserType`, `DiagnosticStatus`)
- **Constantes:** UPPER_SNAKE_CASE (`API_BASE_URL`)

## 🔐 Variables de Entorno

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📚 Recursos

- [Next.js Docs](https://nextjs.org/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Radix UI](https://www.radix-ui.com/)
- [React Hook Form](https://react-hook-form.com/)
