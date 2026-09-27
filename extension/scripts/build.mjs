import esbuild from "esbuild";
import {
    readFileSync,
    writeFileSync,
    mkdirSync,
    copyFileSync,
    cpSync,
} from "fs";

const watch = process.argv.includes("--watch");
const apiBase =
    process.env.API_BASE ||
    "http://localhost:5400";

mkdirSync("dist", {
    recursive: true,
});

const manifest = JSON.parse(
    readFileSync(
        "src/manifest.json",
        "utf8"
    )
);

manifest.host_permissions = [
    `${apiBase}/*`,
];

writeFileSync(
    "dist/manifest.json",
    JSON.stringify(
        manifest,
        null,
        4
    ) + "\n"
);

copyFileSync(
    "src/content.css",
    "dist/content.css"
);

copyFileSync(
    "src/popup.html",
    "dist/popup.html"
);

cpSync(
    "src/icons",
    "dist/icons",
    {
        recursive: true,
    }
);

const buildOptions = {
    entryPoints: [
        "src/content.ts",
        "src/background.ts",
        "src/popup.ts",
    ],
    bundle: true,
    outdir: "dist",
    target: "chrome100",
    define: {
        API_BASE: JSON.stringify(
            apiBase
        ),
    },
};

if (watch) {
    const ctx =
        await esbuild.context(
            buildOptions
        );

    await ctx.watch();

    console.log(
        `[build] watching for changes (API_BASE=${apiBase})...`
    );
} else {
    await esbuild.build(
        buildOptions
    );

    console.log(
        `[build] done (API_BASE=${apiBase})`
    );
}