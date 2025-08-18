import { useState } from "react";
import { register } from "../api/auth";
import { useNavigate } from "react-router-dom";

export default function Register() {
  const [form, setForm] = useState({
    username:"", password:"", email:"",
    first_name:"", last_name:"",
    course:"None", semester:"None", branch:"None", subject:"None",
    role:"teacher"
  });
  const nav = useNavigate();
  const set = (k,v)=>setForm({...form, [k]:v});

  const submit = async (e) => {
    e.preventDefault();
    await register(form);
    nav("/login");
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <form onSubmit={submit} className="w-full max-w-lg grid grid-cols-2 gap-3">
        <h1 className="col-span-2 text-2xl font-semibold mb-2">Register</h1>
        <input className="border p-2" placeholder="Username" onChange={e=>set("username", e.target.value)} />
        <input className="border p-2" placeholder="Email" onChange={e=>set("email", e.target.value)} />
        <input className="border p-2" placeholder="Password" type="password" onChange={e=>set("password", e.target.value)} />
        <input className="border p-2" placeholder="First name" onChange={e=>set("first_name", e.target.value)} />
        <input className="border p-2" placeholder="Last name" onChange={e=>set("last_name", e.target.value)} />

        <select className="border p-2" onChange={e=>set("course", e.target.value)}>
          <option>None</option><option>B.E.</option><option>M.E.</option>
        </select>
        <select className="border p-2" onChange={e=>set("semester", e.target.value)}>
          <option>None</option><option>I</option><option>II</option><option>III</option><option>IV</option><option>V</option><option>VI</option><option>VII</option><option>VIII</option>
        </select>
        <select className="border p-2" onChange={e=>set("branch", e.target.value)}>
          <option>None</option><option>CSE</option><option>IT</option><option>ECE</option><option>EEE</option><option>MECH</option><option>BioTech</option>
        </select>
        <select className="border p-2" onChange={e=>set("subject", e.target.value)}>
          <option>None</option>
          <option>Compiler Design</option>
          <option>Digital Signal Processing</option>
          <option>Cloud Computing</option>
          <option>Agile Development</option>
        </select>
        <select className="border p-2" onChange={e=>set("role", e.target.value)}>
          <option value="teacher">teacher</option>
          <option value="coe">coe</option>
          <option value="superintendent">superintendent</option>
        </select>
        <button className="col-span-2 bg-black text-white py-2 rounded">Create account</button>
      </form>
    </div>
  );
}
