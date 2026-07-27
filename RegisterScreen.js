import React, { useContext, useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView,
  KeyboardAvoidingView, Platform, ActivityIndicator,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { AuthContext } from "../AuthContext";
import { api, errText } from "../api";
import { theme } from "../theme";
import Logo from "../components/Logo";

const emailOk = (v) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v);
const RULES = [
  ["8+ chars", (v) => v.length >= 8],
  ["Uppercase", (v) => /[A-Z]/.test(v)],
  ["Lowercase", (v) => /[a-z]/.test(v)],
  ["Number", (v) => /\d/.test(v)],
  ["Special", (v) => /[^A-Za-z0-9]/.test(v)],
];
const pwOk = (v) => RULES.every(([, f]) => f(v));

export default function RegisterScreen({ navigation }) {
  const { signIn } = useContext(AuthContext);
  const [f, setF] = useState({ name: "", email: "", password: "", confirm: "" });
  const set = (k) => (v) => setF((s) => ({ ...s, [k]: v }));
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function doRegister() {
    setErr("");
    if (!f.name.trim()) return setErr("Please enter your full name.");
    if (!emailOk(f.email)) return setErr("Invalid email format.");
    if (!pwOk(f.password)) return setErr("Password must be 8+ chars with upper, lower, number & special.");
    if (f.password !== f.confirm) return setErr("Passwords do not match.");
    setBusy(true);
    try { const d = await api.register(f.name.trim(), f.email.trim(), f.password, f.confirm); signIn(d.name); }
    catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  }

  return (
    <KeyboardAvoidingView style={s.bg} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled">
        <TouchableOpacity style={s.back} onPress={() => navigation.goBack()}>
          <Ionicons name="arrow-back" size={24} color={theme.pink} />
        </TouchableOpacity>
        <Logo small />
        <Text style={s.create}>Create account</Text>

        <View style={s.field}>
          <Ionicons name="person-outline" size={18} color={theme.muted} />
          <TextInput style={s.input} placeholder="Full Name" value={f.name} onChangeText={set("name")} />
        </View>
        <View style={s.field}>
          <Ionicons name="mail-outline" size={18} color={theme.muted} />
          <TextInput style={s.input} placeholder="Email" autoCapitalize="none" keyboardType="email-address" value={f.email} onChangeText={set("email")} />
        </View>
        <View style={s.field}>
          <Ionicons name="lock-closed-outline" size={18} color={theme.muted} />
          <TextInput style={s.input} placeholder="Password" secureTextEntry={!show} value={f.password} onChangeText={set("password")} />
          <TouchableOpacity onPress={() => setShow(!show)}>
            <Ionicons name={show ? "eye-off-outline" : "eye-outline"} size={18} color={theme.muted} />
          </TouchableOpacity>
        </View>
        <View style={s.rules}>
          {RULES.map(([label, fn]) => {
            const ok = fn(f.password);
            return <Text key={label} style={[s.rule, ok && s.ruleOk]}>{ok ? "✓" : "○"} {label}</Text>;
          })}
        </View>
        <View style={s.field}>
          <Ionicons name="lock-closed-outline" size={18} color={theme.muted} />
          <TextInput style={s.input} placeholder="Confirm Password" secureTextEntry={!show} value={f.confirm} onChangeText={set("confirm")} />
        </View>

        {!!err && <Text style={s.err}>{err}</Text>}

        <TouchableOpacity style={s.btn} onPress={doRegister} disabled={busy}>
          {busy ? <ActivityIndicator color="#fff" /> : <Text style={s.btnText}>Register</Text>}
        </TouchableOpacity>

        <Text style={s.bottomText}>
          Already have an account?{" "}
          <Text style={s.link} onPress={() => navigation.goBack()}>Login</Text>
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  bg: { flex: 1, backgroundColor: theme.pinkTint },
  scroll: { padding: 26, paddingTop: 50, flexGrow: 1 },
  back: { position: "absolute", left: 18, top: 16, zIndex: 2 },
  create: { fontSize: 20, fontWeight: "700", color: theme.ink, textAlign: "center", marginVertical: 14 },
  field: { flexDirection: "row", alignItems: "center", gap: 10, backgroundColor: "#fff",
    borderWidth: 1, borderColor: theme.line, borderRadius: 12, paddingHorizontal: 14, marginBottom: 11 },
  input: { flex: 1, paddingVertical: 13, fontSize: 15 },
  rules: { flexDirection: "row", flexWrap: "wrap", marginBottom: 8, marginTop: -4 },
  rule: { fontSize: 11.5, color: theme.muted, marginRight: 12, marginBottom: 3 },
  ruleOk: { color: "#2e9e5b" },
  err: { color: "#c0392b", fontSize: 13, marginBottom: 8 },
  btn: { backgroundColor: theme.pink, borderRadius: 12, padding: 15, alignItems: "center", marginTop: 4 },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  bottomText: { textAlign: "center", color: theme.muted, marginTop: 18 },
  link: { color: theme.pink, fontWeight: "700" },
});
