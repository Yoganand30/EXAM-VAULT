import client from "./client";

export const login = (username, password) =>
  client.post("login/", { username, password });

export const register = (payload) =>
  client.post("register/", payload);

export const getSubjectCodes = () =>
  client.get("subject-codes/");

// Teacher
export const getTeacherRequests = () =>
  client.get("teacher/requests/");

export const acceptRequest = (id) =>
  client.post(`teacher/requests/${id}/accept/`);

export const uploadPaper = (id, file) => {
  const form = new FormData();
  form.append("paper", file);
  return client.post(`teacher/requests/${id}/upload/`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const getTeacherFinalPapers = () =>
  client.get("teacher/final-papers/");

// COE
export const listRequests = () => client.get("coe/requests/");

export const createRequest = (payload) => {
  // payload: { teacher_username, s_code, deadline, syllabus(File), q_pattern(File) }
  const form = new FormData();
  Object.keys(payload).forEach((k) => form.append(k, payload[k]));
  return client.post("coe/requests/create/", form);
};

export const finalizeRequest = (id) =>
  client.post(`coe/requests/${id}/finalize/`);

// Superintendent
export const listFinalPapers = () =>
  client.get("sup/final-papers/");

export const getDecryptInfo = (paper_id) =>
  client.get(`sup/final-papers/${paper_id}/decrypt-info/`);
