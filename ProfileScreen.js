import React, { useContext, useEffect, useState } from "react";
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView, Modal, TextInput, Alert,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { AuthContext } from "../AuthContext";
import { api, errText } from "../api";
import { theme } from "../theme";

export default function ProfileScreen({ navigation }) {
  const { signOut } = useContext(AuthContext);
  const [me, setMe] = useState({ name: "", email: "", joined: "", bookings: 0 });
  const [cfg, setCfg] = useState(false);
  const [server, setServer] = useState(api.getBaseUrl());
  const [editVisible, setEditVisible] = useState(false);
  const [editName, setEditName] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [editLoading, setEditLoading] = useState(false);

  const loadMe = () => api.me().then((d) => { setMe(d); setEditName(d.name); setEditEmail(d.email); }).catch(() => {});

  useEffect(() => {
    const unsub = navigation.addListener("focus", loadMe);
    return unsub;
  }, [navigation]);

  async function saveServer() {
    const b = await api.setBaseUrl(server);
    setServer(b); setCfg(false);
    Alert.alert("Saved", "Server address set to:\n" + b);
  }

  async function saveProfile() {
    if (!editName.trim()) return Alert.alert("Error", "Full name cannot be empty.");
    if (!editEmail.trim() || !editEmail.includes("@")) return Alert.alert("Error", "Enter a valid email address.");
    setEditLoading(true);
    try {
      await api.updateProfile(editName.trim(), editEmail.trim());
      setMe((m) => ({ ...m, name: editName.trim(), email: editEmail.trim() }));
      setEditVisible(false);
      Alert.alert("Success", "Profile updated successfully.");
    } catch (e) {
      Alert.alert("Error", errText(e));
    } finally {
      setEditLoading(false);
    }
  }

  const initial = (me.name || "U")[0].toUpperCase();

  function Item({ icon, label, onPress, danger }) {
    return (
      <TouchableOpacity style={s.item} onPress={onPress}>
        <Ionicons name={icon} size={20} color={danger ? "#c0392b" : theme.pink} />
        <Text style={[s.itemText, danger && { color: "#c0392b" }]}>{label}</Text>
        <Ionicons name="chevron-forward" size={18} color={theme.muted} />
      </TouchableOpacity>
    );
  }

  return (
    <ScrollView style={{ backgroundColor: theme.bg }} contentContainerStyle={{ paddingBottom: 30 }}>
      <View style={s.headerBg}>
        <Text style={s.headerTitle}>Profile</Text>
        <View style={s.avatar}><Text style={s.avatarText}>{initial}</Text></View>
        <Text style={s.name}>{me.name || "—"}</Text>
        <Text style={s.email}>{me.email}</Text>
      </View>

      <View style={s.statsRow}>
        <View style={s.stat}><Text style={s.statNum}>{me.bookings}</Text><Text style={s.statLabel}>Bookings</Text></View>
        <View style={s.statDivider} />
        <View style={s.stat}><Text style={s.statNum}>{me.joined || "—"}</Text><Text style={s.statLabel}>Member since</Text></View>
      </View>

      <View style={s.menu}>
        <Item icon="bag-handle-outline" label="My Bookings" onPress={() => navigation.navigate("BookingsTab")} />
        <Item icon="create-outline" label="Edit Profile" onPress={() => { setEditName(me.name); setEditEmail(me.email); setEditVisible(true); }} />
        <Item icon="server-outline" label="Server Settings" onPress={() => { setServer(api.getBaseUrl()); setCfg(true); }} />
        <Item icon="information-circle-outline" label="About Smart Style Finder"
          onPress={() => Alert.alert("Smart Style Finder", "AI-powered fashion discovery — search by image or text to find similar dresses.")} />
        <Item icon="log-out-outline" label="Logout" danger onPress={() =>
          Alert.alert("Logout", "Are you sure you want to log out?", [{ text: "Cancel" }, { text: "Logout", style: "destructive", onPress: signOut }])} />
      </View>

      {/* Edit Profile Modal */}
      <Modal visible={editVisible} transparent animationType="fade" onRequestClose={() => setEditVisible(false)}>
        <View style={s.modalBg}>
          <View style={s.modalCard}>
            <Text style={s.modalTitle}>Edit Profile</Text>
            <Text style={s.modalSub}>Update your name or email address.</Text>
            <Text style={s.fieldLabel}>Full Name</Text>
            <TextInput style={s.input} placeholder="Full Name" value={editName}
              onChangeText={setEditName} autoCapitalize="words" />
            <Text style={s.fieldLabel}>Email</Text>
            <TextInput style={s.input} placeholder="Email address" value={editEmail}
              onChangeText={setEditEmail} autoCapitalize="none" keyboardType="email-address" />
            <View style={{ flexDirection: "row", gap: 10, marginTop: 16 }}>
              <TouchableOpacity style={[s.mBtn, s.mBtnOutline, { flex: 1 }]} onPress={() => setEditVisible(false)}>
                <Text style={[s.mBtnText, { color: theme.pink }]}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[s.mBtn, { flex: 1, opacity: editLoading ? 0.6 : 1 }]}
                onPress={saveProfile} disabled={editLoading}>
                <Text style={s.mBtnText}>{editLoading ? "Saving…" : "Save Changes"}</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Server Settings Modal */}
      <Modal visible={cfg} transparent animationType="fade" onRequestClose={() => setCfg(false)}>
        <View style={s.modalBg}>
          <View style={s.modalCard}>
            <Text style={s.modalTitle}>Server Settings</Text>
            <Text style={s.modalSub}>Backend address (only needed for a standalone APK; auto-detected via Expo).</Text>
            <TextInput style={s.input} autoCapitalize="none" keyboardType="url"
              placeholder="http://192.168.1.5:5000" value={server} onChangeText={setServer} />
            <View style={{ flexDirection: "row", gap: 10, marginTop: 12 }}>
              <TouchableOpacity style={[s.mBtn, s.mBtnOutline, { flex: 1 }]} onPress={() => setCfg(false)}>
                <Text style={[s.mBtnText, { color: theme.pink }]}>Cancel</Text></TouchableOpacity>
              <TouchableOpacity style={[s.mBtn, { flex: 1 }]} onPress={saveServer}>
                <Text style={s.mBtnText}>Save</Text></TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  headerBg: { backgroundColor: theme.pinkSoft, alignItems: "center", paddingTop: 56, paddingBottom: 26, borderBottomLeftRadius: 24, borderBottomRightRadius: 24 },
  headerTitle: { fontSize: 22, fontWeight: "800", color: theme.ink, marginBottom: 14 },
  avatar: { width: 84, height: 84, borderRadius: 42, backgroundColor: theme.pink, alignItems: "center", justifyContent: "center" },
  avatarText: { color: "#fff", fontSize: 36, fontWeight: "800" },
  name: { fontSize: 20, fontWeight: "800", color: theme.ink, marginTop: 12 },
  email: { color: theme.muted, marginTop: 2 },
  statsRow: { flexDirection: "row", backgroundColor: "#fff", marginHorizontal: 16, marginTop: -18,
    borderRadius: 16, borderWidth: 1, borderColor: theme.line, padding: 16, alignItems: "center", elevation: 2 },
  stat: { flex: 1, alignItems: "center" },
  statNum: { fontSize: 18, fontWeight: "800", color: theme.pinkDark },
  statLabel: { color: theme.muted, fontSize: 12, marginTop: 2 },
  statDivider: { width: 1, height: 36, backgroundColor: theme.line },
  menu: { marginTop: 20, marginHorizontal: 16, backgroundColor: "#fff", borderRadius: 16, borderWidth: 1, borderColor: theme.line, overflow: "hidden" },
  item: { flexDirection: "row", alignItems: "center", gap: 14, padding: 16, borderBottomWidth: 1, borderBottomColor: theme.line },
  itemText: { flex: 1, fontSize: 15, color: theme.ink, fontWeight: "500" },
  modalBg: { flex: 1, backgroundColor: "rgba(30,18,30,.5)", justifyContent: "center", padding: 22 },
  modalCard: { backgroundColor: "#fff", borderRadius: 16, padding: 22 },
  modalTitle: { fontSize: 19, fontWeight: "800", color: theme.ink },
  modalSub: { color: theme.muted, fontSize: 12.5, marginVertical: 8 },
  fieldLabel: { fontSize: 13, fontWeight: "600", color: theme.ink, marginBottom: 4, marginTop: 8 },
  input: { borderWidth: 1, borderColor: theme.line, borderRadius: 10, padding: 12, fontSize: 14 },
  mBtn: { backgroundColor: theme.pink, borderRadius: 10, padding: 13, alignItems: "center" },
  mBtnOutline: { backgroundColor: "#fff", borderWidth: 1.5, borderColor: theme.pink },
  mBtnText: { color: "#fff", fontWeight: "700" },
});
