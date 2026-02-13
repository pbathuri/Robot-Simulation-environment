import { SceneObject } from '@/app/design/page';

export type RoboDKStatus = { connected: boolean; available: boolean; station_name?: string; robots?: number; robot_names?: string[] };
export type RoboDKRobot = { name: string; num_joints: number; joints: number[] };
export type RoboDKItem = { name: string; type: string };

const BASE_URL = '/api/robodk';

export const robodk = {
  async getStatus(): Promise<RoboDKStatus> {
    return fetch(`${BASE_URL}/status`).then(r => r.json());
  },

  async reconnect(): Promise<RoboDKStatus> {
    return fetch(`${BASE_URL}/reconnect`, { method: 'POST' }).then(r => r.json());
  },

  async getRobots(): Promise<{ robots: RoboDKRobot[] }> {
    return fetch(`${BASE_URL}/robots`).then(r => r.json());
  },

  async getItems(): Promise<{ items: RoboDKItem[] }> {
    return fetch(`${BASE_URL}/items`).then(r => r.json());
  },

  async loadRobot(filter = ''): Promise<{ success: boolean; name?: string; error?: string }> {
    return fetch(`${BASE_URL}/load-robot`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ robot_filter: filter }),
    }).then(r => r.json());
  },

  async importItem(name: string): Promise<{ object?: any; error?: string }> {
    // Encoded name handles slashes and special chars
    return fetch(`${BASE_URL}/import/${encodeURIComponent(name)}`).then(r => r.json());
  },

  async runQuantumDemo(robotName: string, options: { steps?: number; noise_scale?: number } = {}): Promise<{ success: boolean; error?: string }> {
    return fetch(`${BASE_URL}/quantum-demo`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ robot_name: robotName, ...options }),
    }).then(r => r.json());
  }
};
