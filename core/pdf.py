from django.utils import timezone


def _pdf_escape(value):
    return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def delivery_proof_pdf(proof):
    mission = proof.mission
    generated_at = timezone.localtime()
    reference = f"MT-{mission.id:06d}-{proof.id:06d}"
    lines = [
        ("BAOL EXPRESS", 20),
        ("MOTOTRACK", 15),
        ("Preuve officielle de livraison", 14),
        ("", 10),
        (f"Mission : #{mission.id}", 11),
        (f"Client : {mission.nom_client}", 11),
        (f"Adresse : {mission.adresse_livraison}", 11),
        (f"Livreur : {mission.livreur.nom_complet}", 11),
        (f"Moto : {mission.moto.immatriculation}", 11),
        ("OTP valide : Oui", 11),
        (f"Date de livraison : {proof.valide_le:%d/%m/%Y}", 11),
        (f"Heure de livraison : {proof.valide_le:%H:%M:%S}", 11),
        ("", 10),
        ("Document certifie electroniquement", 11),
        ("Signature numerique : MOTOTRACK - BAOL EXPRESS", 11),
        (f"Reference de preuve : {reference}", 10),
        (f"Document genere le : {generated_at:%d/%m/%Y a %H:%M:%S}", 10),
    ]
    commands = ["BT", "/F1 12 Tf", "60 780 Td"]
    first = True
    for text, size in lines:
        if not first:
            commands.append("0 -28 Td")
        commands.extend([f"/F1 {size} Tf", f"({_pdf_escape(text)}) Tj"])
        first = False
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode())
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(pdf)
