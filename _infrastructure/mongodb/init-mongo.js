// Amelanq Netz-Anmeldung - MongoDB Initialisierung
// Laeuft nur beim allerersten Start (leeres Datenverzeichnis).
//
// STAND v0.1: Platzhalter. Collections und Indizes kommen in
// Roadmap-Schritt 1 (Datenmodell: Anlagen, Netzbetreiber, Antraege).

const dbName = process.env.MONGO_INITDB_DATABASE || 'netzanmeldung';
const db = db.getSiblingDB(dbName);

// --- Migrations-Metadaten ---
db.createCollection('schema');
db.schema.updateOne(
  { _id: 'meta' },
  { $setOnInsert: { _id: 'meta', version: 0, appliedAt: new Date() } }
);

print('[init-mongo] Grundgeruest fuer "' + dbName + '" angelegt (v0.1).');
