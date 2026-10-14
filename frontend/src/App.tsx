import AppRoutes from "./routes/AppRoutes";

import {AuthProvider} from "./context/AuthContext";


export default function App() {

  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );

}
