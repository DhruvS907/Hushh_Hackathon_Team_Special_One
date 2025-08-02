// src/pages/Splash.jsx
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "react-bootstrap";
import "bootstrap/dist/css/bootstrap.min.css";
import "../styles/Splash.css";
import Image from "../assets/Brand_logo.png";

function Splash() {
  const navigate = useNavigate();
  const [logoVisible, setLogoVisible] = useState(false);
  const [logoFloatUp, setLogoFloatUp] = useState(false);
  const [buttonsVisible, setButtonsVisible] = useState(false);

  useEffect(() => {
    setTimeout(() => setLogoVisible(true), 500);       // Show logo
    setTimeout(() => setLogoFloatUp(true), 1800);      // Move logo up
    setTimeout(() => setButtonsVisible(true), 2400);   // Show buttons
  }, []);

  const handleClick = (type) => {
    if (type === "new") navigate("/signup");
    else navigate("/signin");
  };

  return (
    <div className="splash-wrapper">
      <div
        className={`logo-container ${logoVisible ? "visible" : ""} ${logoFloatUp ? "float-up" : ""}`}
        id="logo"
      >
        <img className="brand-image" src={Image} alt="Brand" />
        <h1 className="brand-text">Welcome !!</h1>
        <h1 className="brand-text">Consent Scretary Agent</h1>
      </div>

      <div className={`button-container ${buttonsVisible ? "visible" : ""}`}>
        <Button variant="outline-light" className="splash-btn" onClick={() => handleClick("new")}>
          I’m New Here
        </Button>
        <Button variant="outline-light" className="splash-btn" onClick={() => handleClick("existing")}>
          I Already Have an Account
        </Button>
      </div>
    </div>
  );
}

export default Splash;
