import { useEffect, useState } from "react";
import NavBar from "../components/NavBar";
import client from "../api/client";

export default function COE() {
  const role = localStorage.getItem("role");

  // Filters
  const [course, setCourse] = useState("None");
  const [semester, setSemester] = useState("None");
  const [branch, setBranch] = useState("None");
  const [subject, setSubject] = useState("None");

  // teachers + s_code from /coe/teachers/
  const [teachers, setTeachers] = useState([]);
  const [scode, setScode] = useState("");
  const [uploadedReqIds, setUploadedReqIds] = useState([]);

  // files + deadline + chosen teacher
  const [syllabus, setSyllabus] = useState(null);
  const [qPattern, setQPattern] = useState(null);
  const [deadline, setDeadline] = useState("");
  const [teacherId, setTeacherId] = useState("");

  // requests list
  const [requests, setReq] = useState([]);

  const loadRequests = async () => {
    const { data } = await client.get("coe/requests/");
    setReq(data);
  };

  const fetchTeachers = async () => {
    if ([course, semester, branch, subject].some(v => !v || v === "None")) {
      alert("Select course, semester, branch, subject");
      return;
    }
    const { data } = await client.post("coe/teachers/", {
      course, semester, branch, subject
    });
    setTeachers(data.teachers || []);
    setScode(data.s_code || "");
    setUploadedReqIds((data.uploaded_request_ids || []).map(x => x.id));
  };

  const createRequest = async (e) => {
    e.preventDefault();
    if (!teacherId || !scode || !syllabus || !qPattern || !deadline) {
      alert("Please select teacher, choose files and deadline");
      return;
    }
    const form = new FormData();
    form.append("s_code", scode);
    form.append("syllabus", syllabus);
    form.append("q_pattern", qPattern);
    form.append("g_id", teacherId);
    form.append("deadline", deadline);

    await client.post("coe/requests/add/", form);
    alert("Request created");
    setTeacherId("");
    setSyllabus(null);
    setQPattern(null);
    setDeadline("");
    await loadRequests();
  };

  const finalize = async (id) => {
    await client.post(`coe/requests/${id}/finalize/`);
    alert("Finalized");
    await loadRequests();
  };

  useEffect(() => { loadRequests(); }, []);

  const onLogout = ()=>{ localStorage.clear(); window.location.href="/login"; }

  return (
    <div>
      <NavBar role={role} onLogout={onLogout} />

      <div className="p-6 grid gap-8 md:grid-cols-2">
        {/* Left: Filters + Teacher search */}
        <div className="border p-4 rounded space-y-3">
          <h2 className="text-xl font-semibold">Find Teachers</h2>

          <div className="grid grid-cols-2 gap-3">
            <select className="border p-2" value={course} onChange={e=>setCourse(e.target.value)}>
              <option>None</option><option>B.E.</option><option>M.E.</option>
            </select>

            <select className="border p-2" value={semester} onChange={e=>setSemester(e.target.value)}>
              <option>None</option><option>I</option><option>II</option><option>III</option>
              <option>IV</option><option>V</option><option>VI</option><option>VII</option><option>VIII</option>
            </select>

            <select className="border p-2" value={branch} onChange={e=>setBranch(e.target.value)}>
              <option>None</option><option>CSE</option><option>IT</option><option>ECE</option>
              <option>EEE</option><option>MECH</option><option>BioTech</option>
            </select>

            <select className="border p-2" value={subject} onChange={e=>setSubject(e.target.value)}>
              <option>None</option>
              <option>Compiler Design</option>
              <option>Digital Signal Processing</option>
              <option>Cloud Computing</option>
              <option>Agile Development</option>
            </select>
          </div>

          <button className="bg-black text-white px-4 py-2 rounded" onClick={fetchTeachers}>
            Search Teachers
          </button>

          {scode && <div className="text-sm">Subject Code: <b>{scode}</b></div>}

          <div className="mt-3">
            <h3 className="font-medium mb-1">Available Teachers</h3>
            {teachers.length === 0 && <div className="text-sm text-gray-500">No teachers matched or all already requested.</div>}
            <select className="border p-2 w-full" value={teacherId} onChange={e=>setTeacherId(e.target.value)}>
              <option value="">Select teacher</option>
              {teachers.map(t => (
                <option key={t.id} value={t.id}>
                  {t.first_name} {t.last_name} ({t.username}) — {t.teacher_id}
                </option>
              ))}
            </select>
          </div>

          <form onSubmit={createRequest} className="space-y-3">
            <div>
              <label className="text-sm">Deadline</label>
              <input className="border p-2 w-full" type="date" value={deadline} onChange={e=>setDeadline(e.target.value)} />
            </div>
            <div>
              <label className="text-sm">Syllabus</label>
              <input className="block" type="file" onChange={e=>setSyllabus(e.target.files[0])} />
            </div>
            <div>
              <label className="text-sm">Question Pattern</label>
              <input className="block" type="file" onChange={e=>setQPattern(e.target.files[0])} />
            </div>
            <button className="bg-black text-white px-4 py-2 rounded">Create Request</button>
          </form>
        </div>

        {/* Right: Requests list & finalize */}
        <div>
          <h2 className="text-xl font-semibold mb-2">All Requests</h2>
          <div className="space-y-3">
            {requests.map(r => (
              <div key={r.id} className="border p-3 rounded">
                <div className="text-sm">{r.tusername} — {r.s_code}</div>
                <div className="text-sm">Deadline: {r.deadline}</div>
                <div className="text-sm">Status: {r.status}</div>
                {r.status === "Uploaded" && (
                  <button className="mt-2 px-3 py-1 bg-black text-white rounded" onClick={()=>finalize(r.id)}>
                    Finalize
                  </button>
                )}
              </div>
            ))}
            {requests.length === 0 && <div className="text-sm text-gray-500">No requests yet.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
