# 🎓 Guía de Next.js para Principiantes

## 📖 ¿Qué es Next.js?

Next.js es como HTML/CSS/JS tradicional, pero con **superpoderes**:
- No necesitas crear archivos HTML separados
- El CSS puede ir inline con Tailwind
- El JavaScript está integrado en el mismo archivo
- Las rutas se crean automáticamente por carpetas

---

## 🗂️ Estructura de Carpetas = Rutas Automáticas

```
src/app/
├── page.tsx                    → http://localhost:3000/
├── login/
│   └── page.tsx                → http://localhost:3000/login
└── dashboard/
    ├── page.tsx                → http://localhost:3000/dashboard
    ├── admin/
    │   └── page.tsx            → http://localhost:3000/dashboard/admin
    └── clients/
        └── page.tsx            → http://localhost:3000/dashboard/clients
```

**No necesitas configurar rutas** - la carpeta ES la ruta.

---

## 📄 Anatomía de un Archivo .tsx

### Ejemplo: `admin/page.tsx`

```tsx
// ═══════════════════════════════════════════════════════════
// 1️⃣ IMPORTS - Como incluir archivos en HTML tradicional
// ═══════════════════════════════════════════════════════════
import { AdminPanel } from "@/components/features/admin/AdminPanel";
//      ↑ Componente      ↑ Ruta (@ = src/)

// ═══════════════════════════════════════════════════════════
// 2️⃣ FUNCIÓN - Como una página HTML
// ═══════════════════════════════════════════════════════════
export default function AdminPage() {
  //               ↑ Nombre de la función (puede ser cualquiera)
  
  // ═══════════════════════════════════════════════════════════
  // 3️⃣ RETURN - El HTML que se muestra
  // ═══════════════════════════════════════════════════════════
  return <AdminPanel />;
  //     ↑ Componente reutilizable
}
```

### Equivalente HTML Tradicional:

```html
<!-- admin.html -->
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div id="admin-container"></div>
  <script src="js/admin-panel.js"></script>
</body>
</html>
```

---

## 🧩 Componentes Reutilizables

### En Next.js:

```tsx
// components/Button.tsx
export function Button({ text, onClick }) {
  return (
    <button 
      className="bg-blue-500 text-white px-4 py-2 rounded"
      onClick={onClick}
    >
      {text}
    </button>
  );
}

// Usar en cualquier página
import { Button } from '@/components/Button';

function MyPage() {
  return (
    <div>
      <Button text="Guardar" onClick={() => alert('Guardado')} />
      <Button text="Cancelar" onClick={() => alert('Cancelado')} />
    </div>
  );
}
```

### HTML Tradicional (copiar/pegar):

```html
<!-- Copiar esto en cada página -->
<button class="btn-blue" onclick="alert('Guardado')">Guardar</button>
<button class="btn-blue" onclick="alert('Cancelado')">Cancelar</button>
```

---

## 🎨 CSS con Tailwind

En lugar de crear archivos CSS separados, usas clases directamente:

```tsx
<div className="flex h-screen bg-gray-100">
  <h1 className="text-2xl font-bold text-blue-600">Título</h1>
  <button className="bg-green-500 hover:bg-green-600 px-4 py-2 rounded">
    Click
  </button>
</div>
```

**Equivalente CSS tradicional:**

```html
<link rel="stylesheet" href="styles.css">
<div class="container">
  <h1 class="title">Título</h1>
  <button class="btn-green">Click</button>
</div>
```

```css
/* styles.css */
.container { display: flex; height: 100vh; background: #f3f4f6; }
.title { font-size: 1.5rem; font-weight: bold; color: #2563eb; }
.btn-green { background: #10b981; padding: 0.5rem 1rem; border-radius: 0.25rem; }
.btn-green:hover { background: #059669; }
```

---

## 🔄 Estado Reactivo (Variables que Actualizan la Página)

### Next.js:

```tsx
import { useState } from 'react';

export default function Counter() {
  const [count, setCount] = useState(0);  // ← Variable reactiva
  
  return (
    <div>
      <p>Contador: {count}</p>
      <button onClick={() => setCount(count + 1)}>+1</button>
      <button onClick={() => setCount(count - 1)}>-1</button>
    </div>
  );
}
```

### HTML Tradicional:

```html
<div>
  <p>Contador: <span id="count">0</span></p>
  <button onclick="increment()">+1</button>
  <button onclick="decrement()">-1</button>
</div>

<script>
  let count = 0;
  
  function increment() {
    count++;
    document.getElementById('count').innerText = count;
  }
  
  function decrement() {
    count--;
    document.getElementById('count').innerText = count;
  }
</script>
```

---

## 🌐 Llamadas a la API

### Next.js:

```tsx
import { api } from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

export default function UserList() {
  const { data, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: () => api.get('/users')
  });
  
  if (isLoading) return <p>Cargando...</p>;
  
  return (
    <ul>
      {data.map(user => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  );
}
```

### HTML Tradicional:

```html
<div id="user-list">Cargando...</div>

<script>
  fetch('http://localhost:8000/users')
    .then(res => res.json())
    .then(users => {
      const html = users.map(u => `<li>${u.name}</li>`).join('');
      document.getElementById('user-list').innerHTML = `<ul>${html}</ul>`;
    });
</script>
```

---

## 📁 Estructura del Proyecto

```
front/src/
├── app/                        # 📄 PÁGINAS (rutas)
│   ├── page.tsx                # Home
│   ├── login/page.tsx          # Login
│   └── dashboard/
│       ├── page.tsx            # Dashboard principal
│       ├── admin/page.tsx      # Panel admin
│       └── clients/page.tsx    # Lista de clientes
│
├── components/                 # 🧩 COMPONENTES REUTILIZABLES
│   ├── features/               # Por funcionalidad
│   │   ├── admin/              # Componentes de admin
│   │   ├── diagnostics/        # Componentes de diagnósticos
│   │   └── survey/             # Componentes de encuestas
│   ├── layout/                 # Header, Sidebar
│   └── ui/                     # Botones, Badges, etc.
│
├── styles/                     # 🎨 CSS
│   └── globals.css             # Estilos globales
│
├── lib/                        # 🛠️ UTILIDADES
│   ├── api/                    # Cliente HTTP
│   ├── types/                  # Tipos TypeScript
│   └── utils/                  # Funciones helper
│
└── config/                     # ⚙️ CONFIGURACIÓN
    └── pipeline-presets.ts     # Configuración del pipeline
```

---

## 🚀 Comandos Básicos

```bash
# Instalar dependencias (solo la primera vez)
npm install

# Iniciar servidor de desarrollo (auto-recarga)
npm run dev

# Ver en navegador
http://localhost:3000

# Build para producción
npm run build
npm start
```

---

## ✏️ Cómo Editar una Página

### Ejemplo: Cambiar el título de Admin

1. **Abre:** `front/src/app/dashboard/admin/page.tsx`

2. **Encuentra:**
```tsx
export default function AdminPage() {
  return <AdminPanel />;
}
```

3. **Edita:**
```tsx
export default function AdminPage() {
  return (
    <div>
      <h1 className="text-3xl font-bold mb-4">Panel de Administración</h1>
      <AdminPanel />
    </div>
  );
}
```

4. **Guarda** - El navegador se actualiza automáticamente

---

## 🎯 Reglas Importantes

### 1. `className` en lugar de `class`
```tsx
// ✅ Correcto
<div className="bg-blue-500">Hola</div>

// ❌ Incorrecto
<div class="bg-blue-500">Hola</div>
```

### 2. Variables en HTML con `{}`
```tsx
const nombre = "Juan";
return <p>Hola {nombre}</p>;  // ← Muestra: Hola Juan
```

### 3. Imports con `@/`
```tsx
// ✅ Correcto (ruta absoluta)
import { Button } from '@/components/ui/Button';

// ❌ Evitar (ruta relativa)
import { Button } from '../../../components/ui/Button';
```

### 4. Cada componente debe tener un `export default`
```tsx
export default function MyPage() {
  return <div>Contenido</div>;
}
```

---

## 🆘 Errores Comunes

### Error: "Cannot find module"
**Causa:** Ruta de import incorrecta  
**Solución:** Verifica que el archivo exista y la ruta sea correcta

```tsx
// Si el archivo está en: src/components/features/admin/AdminPanel.tsx
import { AdminPanel } from '@/components/features/admin/AdminPanel';
```

### Error: "className is not defined"
**Causa:** Usaste `class` en lugar de `className`  
**Solución:** Cambia `class` por `className`

### Error: "Unexpected token <"
**Causa:** Olvidaste el `return` o las llaves `{}`  
**Solución:**
```tsx
// ❌ Incorrecto
export default function MyPage() {
  <div>Hola</div>
}

// ✅ Correcto
export default function MyPage() {
  return <div>Hola</div>;
}
```

---

## 📚 Recursos

- **Documentación oficial:** https://nextjs.org/docs
- **Tailwind CSS:** https://tailwindcss.com/docs
- **React básico:** https://react.dev/learn

---

## 💡 Consejo Final

**No necesitas aprender todo de una vez.** Empieza editando páginas existentes:

1. Cambia textos
2. Modifica colores (clases de Tailwind)
3. Agrega botones
4. Copia componentes existentes

Con el tiempo entenderás cómo funciona todo. ¡Es más fácil de lo que parece! 🚀
