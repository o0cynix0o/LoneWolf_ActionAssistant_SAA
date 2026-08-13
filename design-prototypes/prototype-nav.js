(() => {
  const revision = "borderless-live";
  const current = new URL(window.location.href);
  if (current.searchParams.get("revision") !== revision) {
    current.searchParams.set("revision", revision);
    window.location.replace(current.href);
    return;
  }

  document.querySelectorAll('a[href$=".html"], a[href*=".html?"]').forEach((link) => {
    const destination = new URL(link.getAttribute("href"), document.baseURI);
    if (destination.origin === window.location.origin && destination.pathname.includes("/design-prototypes/")) {
      destination.searchParams.set("revision", revision);
      link.href = destination.href;
    }
  });
})();
