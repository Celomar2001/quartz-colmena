import { PageLayout, SharedLayout } from "./quartz/cfg"
import * as Component from "./quartz/components"

// components shared across all pages
export const sharedPageComponents: SharedLayout = {
  head: Component.Head(),
  header: [],
  afterBody: [],
  footer: Component.Footer({
    links: {
      GitHub: "https://github.com/jackyzha0/quartz",
      "Discord Community": "https://discord.gg/cRFFHYye7t",
    },
  }),
}

// components for pages that display a single page (e.g. a single note)
export const defaultContentPageLayout: PageLayout = {
  beforeBody: [
    Component.ConditionalRender({
      component: Component.Breadcrumbs(),
      condition: (page) => page.fileData.slug !== "index",
    }),
    Component.ArticleTitle(),
    Component.ContentMeta(),
    Component.TagList(),
  ],
  left: [
    Component.PageTitle(),
    Component.MobileOnly(Component.Spacer()),
    Component.Flex({
      components: [
        {
          Component: Component.Search(),
          grow: true,
        },
        { Component: Component.Darkmode() },
        { Component: Component.ReaderMode() },
      ],
    }),
    Component.Explorer({
      sortFn: (a, b) => {
        const order = ["SPANISH", "ENGLISH", "FRENCH", "PORTUGUESE", "POLSKI"]
        const idxA = order.indexOf(a.displayName.toUpperCase())
        const idxB = order.indexOf(b.displayName.toUpperCase())
        if (idxA === -1 && idxB === -1) return a.displayName.localeCompare(b.displayName)
        if (idxA === -1) return 1
        if (idxB === -1) return -1
        return idxA - idxB
      },
      mapFn: (node) => {
        const nombres: Record<string, string> = {
          "SPANISH": "Español",
          "ENGLISH": "English",
          "FRENCH": "Français",
          "PORTUGUESE": "Português",
          "POLSKI": "Polski",
        }
        const traduccion = nombres[node.displayName.toUpperCase()]
        if (traduccion) node.displayName = traduccion
      },
      order: ["sort", "map"],
    }),
  ],
  right: [
    Component.Graph(),
    Component.DesktopOnly(Component.TableOfContents()),
    Component.Backlinks(),
  ],
}

// components for pages that display lists of pages  (e.g. tags or folders)
export const defaultListPageLayout: PageLayout = {
  beforeBody: [Component.Breadcrumbs(), Component.ArticleTitle(), Component.ContentMeta()],
  left: [
    Component.PageTitle(),
    Component.MobileOnly(Component.Spacer()),
    Component.Flex({
      components: [
        {
          Component: Component.Search(),
          grow: true,
        },
        { Component: Component.Darkmode() },
      ],
    }),
    Component.Explorer(),
  ],
  right: [],
}
