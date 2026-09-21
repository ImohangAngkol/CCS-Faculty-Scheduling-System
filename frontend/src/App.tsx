import AppRoutes from "./routes/AppRoutes";

import {
  GAProvider,
} from "./context/GAContext";


export default function App() {

  return (
    <GAProvider>
      <AppRoutes />
    </GAProvider>
  );

}