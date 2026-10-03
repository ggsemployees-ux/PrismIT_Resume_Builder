import "./PrismLogo.css";

export default function PrismLogo({ size = "md" }) {
  return (
    <div className={`prism-logo prism-logo--${size}`}>
      <img src="/prism-logo.png" alt="Prism IT Hub" />
    </div>
  );
}
