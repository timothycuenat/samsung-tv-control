import axios, { AxiosError } from 'axios';

export type TV = {
  name: string;
  ip: string;
  modelName?: string;
};

export type TVStatus = {
  art_mode: boolean;
  tv_on: boolean;
  raw_device_info: {
    device: {
      name: string;
      modelName: string;
      ip: string;
      type: string;
      [key: string]: any;
    };
    [key: string]: any;
  };
  [key: string]: any;
};

export type APIError = {
  error: string;
  error_type: string;
};

const BASE_URL = 'http://localhost:8080/api';

export class TVService {
  private handleError(error: unknown): never {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<APIError>;
      if (axiosError.response?.data?.error) {
        throw new Error(axiosError.response.data.error);
      }
    }
    throw error;
  }

  async getAllTVs(): Promise<TV[]> {
    try {
      const res = await axios.get(`${BASE_URL}/v1/tvs`);
      return res.data;
    } catch (error) {
      this.handleError(error);
    }
  }

  async getTVStatus(ip: string): Promise<TVStatus> {
    try {
      const res = await axios.get(`${BASE_URL}/v1/tv/${ip}`);
      return res.data;
    } catch (error) {
      this.handleError(error);
    }
  }

  async powerControl(ip: string, action: 'on' | 'off' | 'toggle'): Promise<any> {
    try {
      const res = await axios.put(`${BASE_URL}/v1/tv/${ip}/power`, null, {
        params: { action }
      });
      return res.data;
    } catch (error) {
      this.handleError(error);
    }
  }

  async artMode(ip: string, action: 'on' | 'off' | 'toggle'): Promise<any> {
    try {
      const res = await axios.put(`${BASE_URL}/v1/tv/${ip}/art-mode`, null, {
        params: { action }
      });
      return res.data;
    } catch (error) {
      this.handleError(error);
    }
  }
}

export const tvService = new TVService(); 