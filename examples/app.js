const express = require("express");
const app = express();

// Middleware
app.use(express.json());

app.get("/api/health", (req, res) => {
  res.json({ status: "ok", uptime: process.uptime() });
});

app.post("/api/transform", async (req, res) => {
  const { input, format = "svg" } = req.body;
  const result = await renderCode(input, { format });
  res.type(format).send(result);
});

app.listen(3000, () => {
  console.log("✦ codeframe server running on :3000");
});
