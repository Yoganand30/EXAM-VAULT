import { useEffect, useState } from "react";
import NavBar from "../components/NavBar";
import {
  // NEW endpoints per original dashboard
  getTeacherPending,
  getTeacherAccepted,
  acceptRequest,
  uploadPaper,
} from "./teacher_api";

export default function Teacher() {
  const role = localStorage.getItem("role");
  const [pending, setPending] = useState([]);
  const [accepted, setAccepted] = useState([]);
  const [uploading, setUploading] = useState({}); // id -> bool

  const load = async () => {
    const p = await getTeacherPending();
    const a = await getTeacherAccepted();
    setPending(p);
    setAccepted(a);
  };

  useEffect(() => { load(); }, []);

  const doAccept = async (id) => {
    await acceptRequest(id);
    await load();
  };

  const doUpload = async (id, file) => {
    setUploading({ ...uploading, [id]: true });
    try {
      await uploadPaper(id, file);
      await load();
      alert("Uploaded & recorded on chain");
    } catch (e) {
      alert("Upload failed");
    } finally {
      setUploading({ ...uploading, [id]: false });
    }
  };

  const onLogout = () => {
    localStorage.clear();
    window.location.href = "/login";
  };

  return (
    <div>
      <NavBar role={role} onLogout={onLogout} />
      <div className="p-6 grid gap-8 md:grid-cols-2">
        {/* Pending Requests */}
        <div>
          <h2 className="text-xl font-semibold mb-2">Pending Requests</h2>
          <div className="space-y-3">
            {pending.length === 0 && <div className="text-sm text-gray-500">No pending requests.</div>}
            {pending.map(r => (
              <div key={r.id} className="border p-3 rounded">
                <div className="text-sm">Subject Code: {r.s_code}</div>
                <div className="text-sm">Deadline: {r.deadline}</div>
                <div className="text-sm">Status: {r.status}</div>
                <button className="mt-2 px-3 py-1 bg-black text-white rounded" onClick={()=>doAccept(r.id)}>
                  Accept
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Accepted / Uploaded (no final papers list) */}
        <div>
          <h2 className="text-xl font-semibold mb-2">Accepted / Uploaded</h2>
          <div className="space-y-3">
            {accepted.length === 0 && <div className="text-sm text-gray-500">None.</div>}
            {accepted.map(r => (
              <div key={r.id} className="border p-3 rounded">
                <div className="text-sm">Subject Code: {r.s_code}</div>
                <div className="text-sm">Status: {r.status}</div>
                {r.status === "Accepted" && (
                  <div className="mt-2">
                    <input type="file" onChange={(e)=>doUpload(r.id, e.target.files[0])} />
                    {uploading[r.id] && <div className="text-xs mt-1">Uploading...</div>}
                  </div>
                )}
                {r.status !== "Accepted" && (
                  <div className="text-xs mt-1 italic">No action required</div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
