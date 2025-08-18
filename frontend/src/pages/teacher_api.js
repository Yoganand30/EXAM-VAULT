import client from "../api/client";

export const getTeacherPending = async () => {
  const { data } = await client.get("teacher/requests/pending/");
  return data;
};

export const getTeacherAccepted = async () => {
  const { data } = await client.get("teacher/requests/accepted/");
  return data;
};

export const acceptRequest = (id) =>
  client.post(`teacher/requests/${id}/accept/`);

export const uploadPaper = (id, file) => {
  const form = new FormData();
  form.append("paper", file);
  return client.post(`teacher/requests/${id}/upload/`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};
