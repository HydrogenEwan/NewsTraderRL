// const { VITE_APP_API_ENDPOINT } = import.meta.env;
const VITE_APP_API_ENDPOINT = "/api";
// const VITE_APP_API_ENDPOINT = "http://192.168.1.151:5001/api";

export interface ErrorResponse {
  errorCode: string;
  errorMessage: string;
}

export interface Response<T> {
  result: boolean;
  data?: T | ErrorResponse;

  // errorCode?: string;
  // errorMessage?: string;

  // error?: string;
  // status?: number;
  // timestamp: string;
}

const client = async <T>(
  url: string,
  method: "GET",
  params?: any
): Promise<Response<T>> => {
  const response = await fetch(`${VITE_APP_API_ENDPOINT}/${url}`, {
    method,
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: params !== undefined ? JSON.stringify(params) : undefined,
  });

  return response.json();
};

export default client;
