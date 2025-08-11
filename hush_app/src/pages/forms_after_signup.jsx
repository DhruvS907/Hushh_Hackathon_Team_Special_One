import React, { useState, useContext, useEffect } from "react";
import axios from "axios";
import "../styles/form_after_sign_up.css";
import brandlogo from "../assets/Brand_logo.png";
import { toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import { useNavigate } from "react-router-dom";
import UserContext from "../UserContext/userContext";

function FormSignup() {
  const navigate = useNavigate();
  const { user, setUser } = useContext(UserContext);

  const [formData, setFormData] = useState({
    name: "",
    linkedin: "",
    github: "",
    gmail: "",
  });

  useEffect(() => {
    if (user?.email) {
      setFormData({
        name: user.name || "",
        linkedin: "",
        github: "",
        gmail: user.email,
      });
    } else {
      toast.error("Please sign up first.");
      navigate('/signup');
    }
  }, [user, navigate]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    toast.dismiss();

    try {
      await axios.post("http://localhost:8000/api/signup-details", formData);

      setUser({
        ...user,
        name: formData.name,
        linkedin: formData.linkedin,
        github: formData.github,
      });

      toast.success("🎉 Your details have been saved!", {
        position: "top-center",
        autoClose: 2000,
      });

      setTimeout(() => {
        if (!user.consentToken) {
            toast.info("Please sign in to continue.");
            navigate("/signin");
        } else {
            navigate("/home");
        }
      }, 2000);

    } catch (error) {
      toast.error("Failed to save details. Please try again.", {
        position: "top-center",
        theme: "dark",
      });
      console.error("Error saving user details:", error);
    }
  };

  return (
    <div className="form-container">
      <div className="brand-logo-container">
        <img src={brandlogo} alt="Brand Logo" className="brand-logo" />
      </div>
      <h2>Complete Your Profile</h2>
      <div className="divider">
        <hr className="flex-grow-1" />
        <span className="px-2 text-white fw-lighter">
          Please provide a few more details to continue
        </span>
        <hr className="flex-grow-1" />
      </div>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          name="name"
          placeholder="Full Name"
          value={formData.name}
          onChange={handleInputChange}
          required
        />
        <input
          type="url"
          name="linkedin"
          placeholder="LinkedIn URL"
          value={formData.linkedin}
          onChange={handleInputChange}
          required
        />
        <input
          type="url"
          name="github"
          placeholder="GitHub URL"
          value={formData.github}
          onChange={handleInputChange}
          required
        />
        <input
          type="email"
          name="gmail"
          placeholder="Gmail ID"
          value={formData.gmail}
          readOnly
          className="readonly-input"
        />
        <button type="submit">Submit Details & Continue</button>
      </form>
    </div>
  );
}

export default FormSignup;
