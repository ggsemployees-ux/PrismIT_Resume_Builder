import { createContext, useContext, useEffect, useState } from "react";

const StaffContext = createContext(null);
const STORAGE_KEY = "prism_staff_name";

export function StaffProvider({ children }) {
  const [staffName, setStaffNameState] = useState(() =>
    localStorage.getItem(STORAGE_KEY) || null
  );

  useEffect(() => {
    if (staffName) {
      localStorage.setItem(STORAGE_KEY, staffName);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [staffName]);

  return (
    <StaffContext.Provider value={{ staffName, setStaffName: setStaffNameState }}>
      {children}
    </StaffContext.Provider>
  );
}

export function useStaff() {
  const ctx = useContext(StaffContext);
  if (!ctx) throw new Error("useStaff must be used within a StaffProvider");
  return ctx;
}
