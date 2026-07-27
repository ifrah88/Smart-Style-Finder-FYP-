import React, { useContext, useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView,
  ActivityIndicator, Alert,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import { AuthContext } from "../AuthContext";
import { api, errText } from "../api";
import { theme } from "../theme";

export default function HomeScreen({ navigation }) {
  const { name } = useContext(AuthContext);
  const first = (name || "there").split(" ")[0];
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState("");

  async function textSearch() {
    const text = q.trim();
    if (!text) return;
    setBusy("Searching the collection…");
    try {
      const d = await api.searchText(text);
      navigation.navigate("Results", { type: d.type, results: d.results, query: text });
    } catch (e) { Alert.alert("Error", errText(e)); } finally { setBusy(""); }
  }

  async function imageSearch(fromCamera) {
    const perm = fromCamera
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) { Alert.alert("Permission needed", "Please allow access to continue."); return; }
    const res = fromCamera
      ? await ImagePicker.launchCameraAsync({ quality: 0.8 })
      : await ImagePicker.launchImageLibraryAsync({ quality: 0.8 });
    if (res.canceled) return;
    setBusy("Analysing your photo…");
    try {
      const d = await api.searchImage(res.assets[0].uri);
      navigation.navigate("Results", { type: d.type, results: d.results });
    } catch (e) { Alert.alert("Couldn't search", errText(e)); } finally { setBusy(""); }
  }

  return (
    <View style={{ flex: 1, backgroundColor: theme.bg }}>
      {!!busy && (
        <View style={s.overlay}><ActivityIndicator size="large" color={theme.pink} /><Text style={s.overlayText}>{busy}</Text></View>
      )}
      <ScrollView contentContainerStyle={{ paddingBottom: 24 }}>
        {/* header */}
        <View style={s.header}>
          <View>
            <Text style={s.brand}>SMART STYLE <Text style={{ color: theme.pinkDark }}>FINDER</Text></Text>
            <Text style={s.brandSub}>♥ Find your perfect dress</Text>
          </View>
          <Ionicons name="notifications-outline" size={24} color={theme.pink} />
        </View>

        {/* greeting */}
        <View style={s.greet}>
          <View style={{ flex: 1 }}>
            <Text style={s.greetTitle}>Hello, {first} 👋</Text>
            <Text style={s.greetSub}>What are you looking for today?</Text>
          </View>
          <Text style={s.greetEmoji}>👗</Text>
        </View>

        {/* search by image */}
        <Text style={s.sectionLabel}>🖼️  SEARCH BY IMAGE</Text>
        <View style={s.imageRow}>
          <TouchableOpacity style={s.imageCard} onPress={() => imageSearch(false)}>
            <View style={s.iconCircle}><Ionicons name="image" size={26} color="#fff" /></View>
            <Text style={s.imageCardTitle}>Upload from{"\n"}<Text style={{ fontWeight: "800" }}>Gallery</Text></Text>
            <Text style={s.imageCardSub}>Choose image from your gallery</Text>
          </TouchableOpacity>
          <TouchableOpacity style={s.imageCard} onPress={() => imageSearch(true)}>
            <View style={s.iconCircle}><Ionicons name="camera" size={26} color="#fff" /></View>
            <Text style={s.imageCardTitle}>Capture from{"\n"}<Text style={{ fontWeight: "800" }}>Camera</Text></Text>
            <Text style={s.imageCardSub}>Take a photo using your camera</Text>
          </TouchableOpacity>
        </View>

        {/* search by text */}
        <Text style={s.sectionLabel}>🔍  SEARCH BY TEXT</Text>
        <View style={s.searchBox}>
          <Ionicons name="search" size={18} color={theme.muted} />
          <TextInput style={s.searchInput} placeholder="Search dress by color, fabric, brand…"
            value={q} onChangeText={setQ} onSubmitEditing={textSearch} returnKeyType="search" />
        </View>
        <TouchableOpacity style={s.searchBtn} onPress={textSearch}>
          <Ionicons name="search" size={18} color="#fff" />
          <Text style={s.searchBtnText}>Search</Text>
        </TouchableOpacity>

        {/* promo */}
        <View style={s.promo}>
          <View style={{ flex: 1 }}>
            <Text style={s.promoTitle}>Discover dresses{"\n"}that match your style</Text>
            <Text style={s.promoSub}>Smart search. Perfect match.</Text>
          </View>
          <Text style={s.promoEmoji}>👗👗</Text>
        </View>
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: 20, paddingTop: 54, paddingBottom: 8 },
  brand: { fontFamily: "serif", fontSize: 19, fontWeight: "700", color: theme.ink, letterSpacing: 1 },
  brandSub: { color: theme.pink, fontSize: 11, marginTop: 2 },
  greet: { flexDirection: "row", alignItems: "center", backgroundColor: theme.pinkSoft,
    margin: 16, marginTop: 8, borderRadius: 16, padding: 20 },
  greetTitle: { fontSize: 20, fontWeight: "800", color: theme.ink },
  greetSub: { color: "#5b5360", marginTop: 4 },
  greetEmoji: { fontSize: 44 },
  sectionLabel: { fontWeight: "700", color: theme.pinkDark, fontSize: 12, letterSpacing: 0.5,
    marginLeft: 18, marginTop: 14, marginBottom: 8 },
  imageRow: { flexDirection: "row", gap: 12, paddingHorizontal: 16 },
  imageCard: { flex: 1, backgroundColor: theme.pinkTint, borderRadius: 16, padding: 16, alignItems: "center" },
  iconCircle: { width: 56, height: 56, borderRadius: 28, backgroundColor: theme.pink,
    alignItems: "center", justifyContent: "center", marginBottom: 10 },
  imageCardTitle: { textAlign: "center", color: theme.ink, fontSize: 14, lineHeight: 19 },
  imageCardSub: { textAlign: "center", color: theme.muted, fontSize: 11, marginTop: 4 },
  searchBox: { flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: "#fff",
    borderWidth: 1, borderColor: theme.line, borderRadius: 12, paddingHorizontal: 14,
    marginHorizontal: 16 },
  searchInput: { flex: 1, paddingVertical: 13, fontSize: 14 },
  searchBtn: { flexDirection: "row", gap: 8, backgroundColor: theme.pink, marginHorizontal: 16,
    marginTop: 10, borderRadius: 12, padding: 14, alignItems: "center", justifyContent: "center" },
  searchBtnText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  promo: { flexDirection: "row", alignItems: "center", backgroundColor: theme.pinkSoft,
    margin: 16, borderRadius: 16, padding: 18 },
  promoTitle: { fontSize: 16, fontWeight: "800", color: theme.ink, lineHeight: 22 },
  promoSub: { color: theme.pink, marginTop: 6, fontWeight: "600", fontSize: 12 },
  promoEmoji: { fontSize: 30 },
  overlay: { position: "absolute", zIndex: 10, top: 0, bottom: 0, left: 0, right: 0,
    backgroundColor: "rgba(255,255,255,.75)", alignItems: "center", justifyContent: "center" },
  overlayText: { marginTop: 10, color: theme.muted },
});
