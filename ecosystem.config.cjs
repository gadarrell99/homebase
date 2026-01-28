module.exports = {
  apps: [
    {
      name: "homebase",
      cwd: "/home/cobaltadmin/homebase/backend",
      script: "/home/cobaltadmin/homebase/backend/venv/bin/uvicorn",
      args: "main:app --host 0.0.0.0 --port 8000",
      interpreter: "none"
    }
  ]
}
