import { connect } from "nats";

const STREAM_NAME = "RUNBOOKS";

(async () => {
  try {
    const nc = await connect({ servers: "nats://localhost:4222" });
    console.log(`✅ Connected to ${nc.getServer()}`);

    // JetStream Manager is required for streamInfo and similar methods
    const jsm = await nc.jetstreamManager();

    try {
      const info = await jsm.streams.info(STREAM_NAME);
      console.log(`📦 Stream "${STREAM_NAME}" info:`);
      console.dir(info, { depth: null });
    } catch (err) {
      console.error(`❌ Failed to get stream info for "${STREAM_NAME}":`, err.message);
    }

    await nc.drain();
  } catch (err) {
    console.error("❌ NATS connection error:", err.message);
  }
})();
