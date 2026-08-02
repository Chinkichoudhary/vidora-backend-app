import { Config } from "@remotion/cli/config";
import { enableTailwind } from "@remotion/tailwind-v4";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);

if (process.env.CHROME_BIN) {
  Config.setBrowserExecutable(process.env.CHROME_BIN);
}

Config.setChromiumDisableWebSecurity(true);
Config.setDelayRenderTimeoutInMilliseconds(120000);

Config.overrideWebpackConfig(enableTailwind);