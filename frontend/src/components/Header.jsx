import { Link, useNavigate } from "react-router-dom";
import PrismLogo from "./PrismLogo";
import { useStaff } from "../StaffContext";
import "./Header.css";

export default function Header({ rightSlot }) {
  const { staffName, setStaffName } = useStaff();
  const navigate = useNavigate();

  return (
    <header className="app-header">
      <Link to="/" className="app-header__brand">
        <PrismLogo size="md" />
      </Link>

      <div className="app-header__center">{rightSlot?.center}</div>

      <div className="app-header__right">
        {rightSlot?.action}
        {staffName && (
          <button
            className="app-header__staff"
            title="Switch staff member"
            onClick={() => {
              setStaffName(null);
              navigate("/");
            }}
          >
            {staffName}
          </button>
        )}
      </div>
    </header>
  );
}
