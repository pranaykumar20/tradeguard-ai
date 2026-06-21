/** Dark theme matching TradeGuard design tokens. */
export const clerkAppearance = {
  variables: {
    colorBackground: "#0d1b2d",
    colorInputBackground: "#10233a",
    colorInputText: "#edf6ff",
    colorText: "#edf6ff",
    colorTextSecondary: "#95a7bd",
    colorPrimary: "#26e4c4",
    colorDanger: "#ff5e6c",
    colorSuccess: "#35d07f",
    colorWarning: "#ffb84d",
    borderRadius: "14px",
    fontFamily: "var(--font-geist-sans), Inter, system-ui, sans-serif",
  },
  elements: {
    rootBox: "mx-auto w-full",
    card: "bg-[#0d1b2d] border border-[#203652] shadow-none",
    headerTitle: "text-[#edf6ff] font-extrabold",
    headerSubtitle: "text-[#95a7bd]",
    socialButtonsBlockButton:
      "border border-[#203652] bg-[#10233a] text-[#edf6ff] hover:bg-[#182a42]",
    formFieldInput: "border-[#203652] bg-[#10233a] text-[#edf6ff]",
    formButtonPrimary: "bg-[#26e4c4] text-[#041018] font-bold hover:brightness-110",
    footerActionLink: "text-[#26e4c4] hover:text-[#55b9ff]",
    identityPreviewEditButton: "text-[#26e4c4]",
    formFieldLabel: "text-[#95a7bd]",
    dividerLine: "bg-[#203652]",
    dividerText: "text-[#95a7bd]",
  },
};
