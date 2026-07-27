import React, { useEffect, useState } from "react";
import {
  View, Text, Image, ScrollView, TextInput, TouchableOpacity, StyleSheet, Alert,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { api, errText } from "../api";
import { theme, SWATCH } from "../theme";

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function nextDays(n) {
  const out = [];
  const today = new Date();
  for (let i = 0; i < n; i++) {
    const d = new Date(today);
    d.setDate(today.getDate() + i);
    out.push({
      iso: d.toISOString().slice(0, 10),
      day: DAYS[d.getDay()], date: d.getDate(), month: MONTHS[d.getMonth()],
    });
  }
  return out;
}

export default function BookingScreen({ route, navigation }) {
  const p = route.params?.product || {};
  const days = nextDays(14);
  const [date, setDate] = useState(days[0].iso);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.me().then((u) => { setName(u.name || ""); setEmail(u.email || ""); }).catch(() => {});
  }, []);

  async function confirm() {
    if (!phone.trim()) { Alert.alert("Booking", "Please enter your phone number."); return; }
    setBusy(true);
    try {
      await api.book(p.product_id, date, "M", phone.trim(), note.trim());
      Alert.alert("✅ Booking Confirmed", "Your dress has been booked! View it under Bookings.",
        [{ text: "OK", onPress: () => navigation.popToTop() }]);
    } catch (e) { Alert.alert("Error", errText(e)); } finally { setBusy(false); }
  }

  return (
    <ScrollView style={{ backgroundColor: theme.bg }} contentContainerStyle={{ padding: 16, paddingBottom: 30 }}>
      {/* product summary */}
      <View style={s.summary}>
        <Image source={{ uri: api.imgUrl(p.img_url) }} style={s.thumb} />
        <View style={{ flex: 1 }}>
          <Text style={s.sTitle} numberOfLines={2}>{p.title}</Text>
          <Text style={s.sBrand}>{p.brand}</Text>
          <View style={s.fabricTag}><Text style={s.fabricText}>{p.fabric}</Text></View>
          <View style={s.metaRow}>
            <View style={[s.dot, { backgroundColor: SWATCH[p.colour] || "#ccc" }]} />
            <Text style={s.colour}>{p.colour}</Text>
          </View>
          <Text style={s.sPrice}>{p.price}</Text>
        </View>
      </View>

      {/* date */}
      <Text style={s.section}><Ionicons name="calendar-outline" size={16} color={theme.pink} />  Select Booking Date</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginTop: 8 }}>
        {days.map((d) => {
          const on = d.iso === date;
          return (
            <TouchableOpacity key={d.iso} style={[s.day, on && s.dayOn]} onPress={() => setDate(d.iso)}>
              <Text style={[s.dayName, on && { color: "#fff" }]}>{d.day}</Text>
              <Text style={[s.dayNum, on && { color: "#fff" }]}>{d.date}</Text>
              <Text style={[s.dayMon, on && { color: "#fff" }]}>{d.month}</Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* your details */}
      <Text style={s.section}><Ionicons name="person-outline" size={16} color={theme.pink} />  Your Details</Text>
      <View style={s.field}>
        <Ionicons name="person-outline" size={16} color={theme.muted} />
        <View style={{ flex: 1 }}>
          <Text style={s.fieldLabel}>Full Name</Text>
          <TextInput style={s.input} value={name} onChangeText={setName} placeholder="Full Name" />
        </View>
      </View>
      <View style={s.field}>
        <Ionicons name="call-outline" size={16} color={theme.muted} />
        <View style={{ flex: 1 }}>
          <Text style={s.fieldLabel}>Phone Number</Text>
          <TextInput style={s.input} value={phone} onChangeText={setPhone} keyboardType="phone-pad" placeholder="+92 300 1234567" />
        </View>
      </View>
      <View style={s.field}>
        <Ionicons name="mail-outline" size={16} color={theme.muted} />
        <View style={{ flex: 1 }}>
          <Text style={s.fieldLabel}>Email Address</Text>
          <TextInput style={s.input} value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" placeholder="you@email.com" />
        </View>
      </View>

      {/* note */}
      <Text style={s.section}><Ionicons name="document-text-outline" size={16} color={theme.pink} />  Additional Note (Optional)</Text>
      <TextInput style={s.noteInput} multiline placeholder="Any special instructions…" value={note} onChangeText={setNote} />

      <TouchableOpacity style={s.confirm} onPress={confirm} disabled={busy}>
        <Ionicons name="calendar" size={18} color="#fff" />
        <Text style={s.confirmText}>  {busy ? "Booking…" : "Confirm Booking"}</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  summary: { flexDirection: "row", gap: 12, backgroundColor: theme.pinkTint, borderRadius: 14, padding: 12 },
  thumb: { width: 86, height: 110, borderRadius: 10, backgroundColor: "#fff" },
  sTitle: { fontWeight: "700", color: theme.ink },
  sBrand: { color: theme.muted, fontSize: 12 },
  fabricTag: { alignSelf: "flex-start", backgroundColor: theme.pinkSoft, borderRadius: 6, paddingHorizontal: 8, paddingVertical: 2, marginTop: 4 },
  fabricText: { color: theme.pinkDark, fontSize: 11, textTransform: "capitalize" },
  metaRow: { flexDirection: "row", alignItems: "center", marginTop: 4 },
  dot: { width: 11, height: 11, borderRadius: 6, marginRight: 6 },
  colour: { fontSize: 12.5, color: "#5b5360", textTransform: "capitalize" },
  sPrice: { fontWeight: "800", color: theme.pinkDark, marginTop: 4, fontSize: 16 },
  section: { fontWeight: "700", color: theme.pink, marginTop: 20, fontSize: 15 },
  day: { width: 58, paddingVertical: 12, borderRadius: 12, borderWidth: 1, borderColor: theme.line, alignItems: "center", marginRight: 8, backgroundColor: "#fff" },
  dayOn: { backgroundColor: theme.pink, borderColor: theme.pink },
  dayName: { fontSize: 12, color: theme.muted },
  dayNum: { fontSize: 18, fontWeight: "800", color: theme.ink, marginVertical: 2 },
  dayMon: { fontSize: 11, color: theme.muted },
  field: { flexDirection: "row", alignItems: "center", gap: 10, backgroundColor: "#fff", borderWidth: 1, borderColor: theme.line, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 6, marginTop: 10 },
  fieldLabel: { fontSize: 11, color: theme.muted },
  input: { fontSize: 15, color: theme.ink, paddingVertical: 4 },
  noteInput: { backgroundColor: "#fff", borderWidth: 1, borderColor: theme.line, borderRadius: 12, padding: 14, minHeight: 70, marginTop: 8, textAlignVertical: "top" },
  confirm: { flexDirection: "row", justifyContent: "center", alignItems: "center", backgroundColor: theme.pink, borderRadius: 12, padding: 16, marginTop: 22 },
  confirmText: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
