const NETWORKS_KEY = 'vpluse_office_networks_v1';
const CURRENT_NETWORK_HINT_KEY = 'vpluse_current_network_hint_v1';

const DEFAULT_NETWORKS = [
  { id: 'n1', name: 'Office WiFi 10.x', cidr: '10.0.0.0/8', active: true },
  { id: 'n2', name: 'Office WiFi 172.16-31', cidr: '172.16.0.0/12', active: true },
  { id: 'n3', name: 'Office WiFi 192.168', cidr: '192.168.0.0/16', active: true },
];

const readJson = (key, fallback) => {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw);
    return parsed ?? fallback;
  } catch {
    return fallback;
  }
};

const writeJson = (key, value) => {
  localStorage.setItem(key, JSON.stringify(value));
};

const ipToInt = (ip) => {
  if (!ip || typeof ip !== 'string') return null;
  const parts = ip.trim().split('.');
  if (parts.length !== 4) return null;
  const nums = parts.map(Number);
  if (nums.some((n) => Number.isNaN(n) || n < 0 || n > 255)) return null;
  return (
    ((nums[0] << 24) >>> 0) +
    ((nums[1] << 16) >>> 0) +
    ((nums[2] << 8) >>> 0) +
    (nums[3] >>> 0)
  ) >>> 0;
};

export const isValidIPv4 = (ip) => ipToInt(ip) != null;

export const isValidCIDR = (cidr) => {
  if (!cidr || typeof cidr !== 'string' || !cidr.includes('/')) return false;
  const [ip, prefixRaw] = cidr.trim().split('/');
  const prefix = Number(prefixRaw);
  if (!Number.isInteger(prefix) || prefix < 0 || prefix > 32) return false;
  return isValidIPv4(ip);
};

export const isIpInCidr = (ip, cidr) => {
  if (!isValidIPv4(ip) || !isValidCIDR(cidr)) return false;
  const [baseIp, prefixRaw] = cidr.trim().split('/');
  const prefix = Number(prefixRaw);
  const ipInt = ipToInt(ip);
  const baseInt = ipToInt(baseIp);
  const mask = prefix === 0 ? 0 : ((0xffffffff << (32 - prefix)) >>> 0);
  return (ipInt & mask) === (baseInt & mask);
};

export const getOfficeNetworks = () => {
  const data = readJson(NETWORKS_KEY, DEFAULT_NETWORKS);
  return Array.isArray(data) ? data : DEFAULT_NETWORKS;
};

export const saveOfficeNetworks = (networks) => {
  writeJson(NETWORKS_KEY, networks);
};

export const addOfficeNetwork = ({ name, cidr, active = true }) => {
  const next = [
    ...getOfficeNetworks(),
    {
      id: `net-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      name: (name || '').trim(),
      cidr: (cidr || '').trim(),
      active: Boolean(active),
    },
  ];
  saveOfficeNetworks(next);
  return next;
};

export const toggleOfficeNetwork = (id) => {
  const next = getOfficeNetworks().map((n) => (
    n.id === id ? { ...n, active: !n.active } : n
  ));
  saveOfficeNetworks(next);
  return next;
};

export const removeOfficeNetwork = (id) => {
  const next = getOfficeNetworks().filter((n) => n.id !== id);
  saveOfficeNetworks(next);
  return next;
};

export const getCurrentNetworkHint = () => {
  const raw = localStorage.getItem(CURRENT_NETWORK_HINT_KEY);
  return raw || '192.168.1.10';
};

export const setCurrentNetworkHint = (value) => {
  localStorage.setItem(CURRENT_NETWORK_HINT_KEY, (value || '').trim());
};

export const verifyOfficeNetworkByIp = (ip) => {
  const ipClean = (ip || '').trim();
  if (!isValidIPv4(ipClean)) {
    return { ok: false, reason: 'invalid_ip', network: null };
  }
  const match = getOfficeNetworks().find((n) => n.active && isIpInCidr(ipClean, n.cidr));
  if (!match) return { ok: false, reason: 'not_whitelisted', network: null };
  return { ok: true, reason: 'ok', network: match };
};
