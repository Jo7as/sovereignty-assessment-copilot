// Beschriftungen der Fundarten des Außenscans
export const RECORD_LABEL: Record<string, string> = {
  MX: "Mailserver",
  SPF: "SPF-Eintrag",
  SPF_NET: "Netz eines E-Mail-Absenders",
  NS: "Nameserver",
  CAA: "Zertifizierungsstelle",
  CNAME: "Weiterleitung der Website",
  ASN: "Netz der Website",
  WEB: "Von der Website geladen",
  SCRIPT: "Im Tag Manager oder Seitencode",
  TECH: "Technik der Website",
};

export const JURISDICTION: Record<string, string> = {
  EU_EWR: "EU",
  ANGEMESSEN: "Angemessenheitsbeschluss",
  USA: "USA · CLOUD Act",
  DRITTSTAAT: "Drittstaat",
};
