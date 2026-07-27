import React, { useContext, useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView,
  KeyboardAvoidingView, Platform, ActivityIndicator, Modal,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { AuthContext } from "../AuthContext";
import { api, errText } from "../api";
import { theme } from "../theme";
import Logo from "../components/Logo";

const emailOk = (v) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v);
const pwOk = (v) => /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/.test(v);

export default function LoginScreen({ navigation }) {
  const { signIn } = useContext(AuthContext);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const [fp, setFp] = useState(false);
  const [fpEmail, setFpEmail] = useState("");
  const [fpPass, setFpPass] = useState("");
  const [fpMsg, setFpMsg] = useState("");

  const [cfg, setCfg] = useState(false);
  const [server, setServer] = useState(api.getBaseUrl());
  async function saveServer() {
    const b = await api.setBaseUrl(server);
    setServer(b); setCfg(false);
  }

  async function doLogin() {
    setErr("");
    if (!email) return setErr("Please enter your email address.");
    if (!emailOk(email)) return setErr("Invalid email format.");
    if (!password) return setErr("Please enter your password.");
    setBusy(true);
    try { const d = await api.login(email.trim(), password); signIn(d.name); }
    catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  }

  async function doForgot() {
    setFpMsg("");
    if (!emailOk(fpEmail)) return setFpMsg("Invalid email format.");
    if (!pwOk(fpPass)) return setFpMsg("Password needs 8+ chars, upper, lower, number & special.");
    try { const d = await api.forgot(fpEmail.trim(), fpPass); setFpMsg("✓ " + (d.message || "Password reset.")); }
    catch (e) { setFpMsg(errText(e)); }
  }

  return (
    <KeyboardAvoidingView style={s.bg} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled">
        <Logo />
        <Text style={s.welcome}>Welcome Back!</Text>
        <Text style={s.sub}>Login to continue</Text>

        <View style={s.field}>
          <Ionicons name="mail-outline" size={18} color={theme.muted} />
          <TextInput style={s.input} placeholder="Email" autoCapitalize="none"
            keyboardType="email-address" value={email} onChangeText={setEmail} />
        </View>
        <View style={s.field}>
          <Ionicons name="lock-closed-outline" size={18} color={theme.muted} />
          <TextInput style={s.input} placeholder="Password" secureTextEntry={!show}
            value={password} onChangeText={setPassword} />
          <TouchableOpacity onPress={() => setShow(!show)}>
            <Ionicons name={show ? "eye-off-outline" : "eye-outline"} size={18} color={theme.muted} />
          </TouchableOpacity>
        </View>

        <TouchableOpacity onPress={() => { setFp(true); setFpEmail(email); }}>
          <Text style={s.forgot}>Forgot Password?</Text>
        </TouchableOpacity>

        {!!err && <Text style={s.err}>{err}</Text>}

        <TouchableOpacity style={s.btn} onPress={doLogin} disabled={busy}>
          {busy ? <ActivityIndicator color="#fff" /> : <Text style={s.btnText}>Login</Text>}
        </TouchableOpacity>

        <View style={s.orRow}>
          <View style={s.line} /><Text style={s.or}>OR</Text><View style={s.line} />
        </View>

        <Text style={s.bottomText}>
          Don't have an account?{" "}
          <Text style={s.link} onPress={() => navigation.navigate("Register")}>Register</Text>
        </Text>

        <TouchableOpacity onPress={() => { setServer(api.getBaseUrl()); setCfg(true); }} style={{ marginTop: 20 }}>
          <Text style={s.cfgLink}>⚙ Server settings</Text>
        </TouchableOpacity>
      </ScrollView>

      <Modal visible={fp} transparent animationType="fade" onRequestClose={() => setFp(false)}>
        <View style={s.modalBg}>
          <View style={s.modalCard}>
            <Text style={s.modalTitle}>Reset Password</Text>
            <View style={s.field}>
              <Ionicons name="mail-outline" size={18} color={theme.muted} />
              <TextInput style={s.input} placeholder="Email" autoCapitalize="none" value={fpEmail} onChangeText={setFpEmail} />
            </View>
            <View style={s.field}>
              <Ionicons name="lock-closed-outline" size={18} color={theme.muted} />
              <TextInput style={s.input} placeholder="New password" secureTextEntry value={fpPass} onChangeText={setFpPass} />
            </View>
            {!!fpMsg && <Text style={[s.err, fpMsg.startsWith("✓") && { color: "#2e9e5b" }]}>{fpMsg}</Text>}
            <View style={{ flexDirection: "row", gap: 10, marginTop: 8 }}>
              <TouchableOpacity style={[s.btn, s.btnOutline, { flex: 1 }]} onPress={() => setFp(false)}>
                <Text style={[s.btnText, { color: theme.pink }]}>Close</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[s.btn, { flex: 1 }]} onPress={doForgot}>
                <Text style={s.btnText}>Reset</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <Modal visible={cfg} transparent animationType="fade" onRequestClose={() => setCfg(false)}>
        <View style={s.modalBg}>
          <View style={s.modalCard}>
            <Text style={s.modalTitle}>Server Settings</Text>
            <Text style={{ color: theme.muted, fontSize: 12.5, marginBottom: 10 }}>
              Backend address (your ngrok URL). Update it here if it changes — no rebuild needed.
            </Text>
            <View style={s.field}>
              <Ionicons name="server-outline" size={18} color={theme.muted} />
              <TextInput style={s.input} autoCapitalize="none" keyboardType="url"
                placeholder="https://your-name.ngrok-free.dev" value={server} onChangeText={setServer} />
            </View>
            <View style={{ flexDirection: "row", gap: 10, marginTop: 8 }}>
              <TouchableOpacity style={[s.btn, s.btnOutline, { flex: 1 }]} onPress={() => setCfg(false)}>
                <Text style={[s.btnText, { color: theme.pink }]}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[s.btn, { flex: 1 }]} onPress={saveServer}>
                <Text style={s.btnText}>Save</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  bg: { flex: 1, backgroundColor: theme.pinkTint },
  scroll: { padding: 26, paddingTop: 70, flexGrow: 1 },
  welcome: { fontSize: 26, fontWeight: "800", color: theme.ink, marginTop: 10 },
  sub: { color: theme.muted, marginBottom: 18 },
  field: { flexDirection: "row", alignItems: "center", gap: 10, backgroundColor: "#fff",
    borderWidth: 1, borderColor: theme.line, borderRadius: 12, paddingHorizontal: 14, marginBottom: 12 },
  input: { flex: 1, paddingVertical: 14, fontSize: 15 },
  forgot: { color: theme.pink, fontWeight: "600", textAlign: "right", marginBottom: 14 },
  err: { color: "#c0392b", fontSize: 13, marginBottom: 8 },
  btn: { backgroundColor: theme.pink, borderRadius: 12, padding: 15, alignItems: "center" },
  btnOutline: { backgroundColor: "#fff", borderWidth: 1.5, borderColor: theme.pink },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  orRow: { flexDirection: "row", alignItems: "center", gap: 12, marginVertical: 20 },
  line: { flex: 1, height: 1, backgroundColor: theme.line },
  or: { color: theme.muted, fontWeight: "600" },
  bottomText: { textAlign: "center", color: theme.muted },
  link: { color: theme.pink, fontWeight: "700" },
  cfgLink: { textAlign: "center", color: theme.muted, fontSize: 13 },
  modalBg: { flex: 1, backgroundColor: "rgba(30,18,30,.5)", justifyContent: "center", padding: 22 },
  modalCard: { backgroundColor: "#fff", borderRadius: 16, padding: 22 },
  modalTitle: { fontSize: 20, fontWeight: "800", color: theme.ink, marginBottom: 12 },
});
