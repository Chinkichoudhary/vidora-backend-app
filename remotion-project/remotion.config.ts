import {Config} from "@remotion/cli/config";
import {enableTailwind} from "@remotion/tailwind-v4";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.overrideWebpackConfig(enableTailwind);

// ADD THESE
//Config.setBrowserExecutable("/usr/bin/chromium");
Config.setChromiumDisableWebSecurity(true);
Config.setDelayRenderTimeoutInMilliseconds(120000);