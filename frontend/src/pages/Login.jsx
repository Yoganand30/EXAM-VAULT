import { useState } from "react";
import { login } from "../api/auth";
import { useNavigate } from "react-router-dom";

export default function Login() {
  const [username, setU] = useState("");
  const [password, setP] = useState("");
  const [error, setError] = useState("");
  const nav = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const { data } = await login(username, password);
      localStorage.setItem("access", data.tokens.access);
      localStorage.setItem("refresh", data.tokens.refresh);
      localStorage.setItem("role", data.role);
      localStorage.setItem("username", data.username);

      if (data.role === "teacher") nav("/teacher");
      else if (data.role === "coe") nav("/coe");
      else nav("/superintendent");
    } catch (err) {
      setError("Invalid credentials");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4">
        <h1 className="text-2xl font-semibold">Login</h1>
        {error && <div className="text-red-600 text-sm">{error}</div>}
        <input className="border w-full p-2" placeholder="Username" value={username} onChange={(e)=>setU(e.target.value)} />
        <input className="border w-full p-2" placeholder="Password" type="password" value={password} onChange={(e)=>setP(e.target.value)} />
        <button className="w-full bg-black text-white py-2 rounded">Sign in</button>
      </form>
    </div>
  );
}
