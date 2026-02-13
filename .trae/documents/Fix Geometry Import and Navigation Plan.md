# Fix Geometry Import and Navigation

## 1. Frontend: Enable STL Geometry Loading
We will modify `apps/web/src/app/design/page.tsx` to support loading actual 3D files exported from RoboDK.

### A. Imports & Types
- Import `STLLoader` from `three-stdlib`.
- Import `useLoader` from `@react-three/fiber`.
- Import `Suspense` from `react`.
- Update `SceneObject` type:
  - Add `meshUrl?: string`.
  - Add `'file'` to `geometry` union type.

### B. `rdkImportItem` Logic Update
- Modify the function to perform a second fetch to `/api/robodk/export/{name}`.
- Convert the response to a Blob and create a local object URL (`URL.createObjectURL`).
- Initialize the new object with:
  - `geometry: 'file'`
  - `meshUrl: url`
  - `scale: [0.001, 0.001, 0.001]` (assuming RoboDK exports in mm and we use meters).

### C. New `STLMesh` Component
- Create a sub-component that uses `useLoader(STLLoader, url)`.
- Wraps the geometry in a `<mesh>`.
- Centers the geometry if needed (optional, but RoboDK exports usually preserve origin).

### D. Update `ObjMesh` and Rendering
- In `ObjMesh`, handle the `file` geometry case by rendering `STLMesh`.
- Wrap the list of objects in `<Suspense fallback={null}>` inside the `<Canvas>` to handle the async loading of STLs.

## 2. Frontend: Improve Navigation
We will tune the `OrbitControls` in `apps/web/src/app/design/page.tsx`.

- Set `enableZoom={true}`.
- Set `zoomSpeed={1.2}` for better responsiveness.
- Set `minDistance={0.1}` and `maxDistance={10}` to prevent clipping or getting lost.
- (Optional) Configure mouse buttons to match standard CAD feel if requested (Left: Rotate, Middle: Pan, Right: Zoom or similar). For now, we'll stick to standard OrbitControls defaults but ensure they are active.

## 3. Backend
- No changes required in Phase 1 (The existing `export_item` endpoint is sufficient).
