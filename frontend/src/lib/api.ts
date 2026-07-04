import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 401) {
      window.location.href = "/login";
      return Promise.reject(error);
    }
    if (status === 403) {
      console.error("Akses ditolak");
    }
    return Promise.reject(error);
  }
);

export default api;
