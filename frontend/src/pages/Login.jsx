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

      const access = data.access || (data.tokens && data.tokens.access);
      const refresh = data.refresh || (data.tokens && data.tokens.refresh);

      if (!access || !refresh) {
        throw new Error("Invalid login response from server");
      }

      localStorage.setItem("access", access);
      localStorage.setItem("refresh", refresh);
      localStorage.setItem("role", data.role);
      localStorage.setItem("username", data.username);

      if (data.role === "teacher") nav("/teacher");
      else if (data.role === "coe") nav("/coe");
      else nav("/superintendent");
    } catch (err) {
      console.error("Login failed:", err);
      setError("Invalid username or password");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 p-4">
      <div className="w-full max-w-md bg-white shadow-lg rounded-2xl p-8">
        <h1 className="text-3xl font-bold text-gray-800 text-center mb-6">
          EXAM-VAULT 
        </h1>
        <form onSubmit={submit} className="space-y-4">
          {error && (
            <div className="text-red-600 text-sm text-center bg-red-50 border border-red-200 p-2 rounded">
              {error}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Username
            </label>
            <input
              className="border w-full p-2 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setU(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              className="border w-full p-2 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
              placeholder="Enter your password"
              type="password"
              value={password}
              onChange={(e) => setP(e.target.value)}
            />
          </div>
          <button
            className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg font-medium transition"
          >
            Sign in
          </button>
        </form>
      </div>
    </div>
  );
}
