# Use an official Node image as the base.
# 'node:18-alpine' is a lightweight (Alpine Linux) image with Node 18 installed.
# Alpine images are smaller but sometimes require extra native build tools
# if an npm dependency needs compilation.
FROM node:18-alpine

# Set the working directory inside the container. All subsequent commands
# (COPY, RUN, etc.) execute relative to /app.
WORKDIR /app

# Copy package.json and package-lock.json (if present) into the image.
# Why copy only these files first?
# - This lets Docker cache the `npm install` layer when your application
#   source code changes but dependencies do not. That speeds up iterative builds.
COPY package*.json ./

# Install JavaScript dependencies declared in package.json.
# In a Docker build this runs `npm install` inside the container.
# Note:
# - On Alpine, some packages that use native addons may fail unless
#   build tools are available (gcc, make, python). For dev projects
#   it's usually fine; if students add native modules, consider using
#   `node:18` (Debian) or add build tools here.
RUN npm install

# Copy the rest of the application source code into the image.
# This includes src/, public/, vite.config.js, and any other files you have.
COPY . .

# Expose port 3000 inside the container.
# This does NOT publish the port to the host by itself — docker run / compose
# must map it (e.g., "3000:3000") to make it accessible on localhost.
EXPOSE 3000

# Default command to run when the container starts.
# - Uses the exec (JSON) form so the PID 1 process is the Node/Vite process.
# - "npm run dev" starts the Vite dev server (development mode).
# - The "--" separates npm args from the script and passes "--host" to Vite,
#   making the dev server bind to 0.0.0.0 so it is reachable from outside
#   the container (important when running inside Docker).
CMD ["npm", "run", "dev", "--", "--host"]
