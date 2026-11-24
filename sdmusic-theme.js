(function () {
  "use strict";

  const root = document.documentElement;
  const repeats = new Set(["no-repeat", "repeat", "repeat-x", "repeat-y", "space", "round"]);
  const hexColor = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;
  const sizeValue = /^(?:\d+(?:\.\d+)?|\.\d+)(?:px|rem|em|%)$/i;
  const setting = (element, name) => (element?.getAttribute(name) || "").trim();

  function imageURL(value, base) {
    if (!value) return "";
    try {
      const url = new URL(value, base);
      if (url.username || url.password) return "";
      if (url.protocol === "https:" ||
          (url.protocol === "http:" && url.origin === new URL(base).origin)) {
        return url.href;
      }
    } catch {
      // Leave an invalid URL unset.
    }
    return "";
  }

  function inkFor(color) {
    let hex = color.slice(1);
    if (hex.length === 3) hex = Array.from(hex, digit => digit.repeat(2)).join("");
    const [r, g, b] = hex.match(/../g).map(pair => {
      const v = parseInt(pair, 16) / 255;
      return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b < 0.179 ? "light" : "dark";
  }

  async function loadTheme() {
    const response = await fetch("sdmusic-theme.xml");
    if (!response.ok) return;
    const xml = new DOMParser().parseFromString(await response.text(), "application/xml");
    const theme = xml.documentElement;
    if (theme.localName !== "sdmusic-theme" || xml.querySelector("parsererror")) return;

    const background = theme.querySelector("background");
    const backgroundColor = setting(background, "color");
    if (hexColor.test(backgroundColor)) {
      root.style.setProperty("--theme-background-color", backgroundColor);
      root.dataset.themeInk = inkFor(backgroundColor);
    }
    const backgroundImage = imageURL(setting(background, "image"), response.url);
    if (backgroundImage) {
      root.style.setProperty("--theme-background-image", `url(${JSON.stringify(backgroundImage)})`);
    }
    const repeat = setting(background, "repeat").toLowerCase();
    if (repeats.has(repeat)) root.style.setProperty("--theme-background-repeat", repeat);

    const links = theme.querySelector("links");
    const color = setting(links, "color");
    const size = setting(links, "size");
    if (hexColor.test(color)) root.style.setProperty("--theme-link-color", color);
    if (sizeValue.test(size) && parseFloat(size) > 0) root.style.setProperty("--theme-link-size", size);

    const top = theme.querySelector("top-image");
    const src = imageURL(setting(top, "src"), response.url);
    if (!src) return;
    const image = document.getElementById("top-image");
    image.alt = setting(top, "alt");
    image.onload = () => { image.parentElement.hidden = false; };
    image.onerror = () => { image.parentElement.hidden = true; };
    image.src = src;
  }

  loadTheme().catch(() => {
    // The theme is optional; failure must not affect the listings.
  });
})();
