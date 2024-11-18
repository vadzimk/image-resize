FROM node:22.2.0 AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

COPY ./frontend /usr/src/app/
WORKDIR /usr/src/app

FROM base AS dependencies
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --prod --frozen-lockfile

FROM base as build
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile
RUN pnpm run build


FROM nginx 
COPY --from=dependencies /usr/src/app/node_modules /usr/src/app/node_modules
COPY --from=build /usr/src/app/dist/ /usr/share/nginx/html/
COPY ./nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
# for debugging only
# CMD ["tail", "-f", "/dev/null"]
CMD ["nginx", "-g", "daemon off;"]