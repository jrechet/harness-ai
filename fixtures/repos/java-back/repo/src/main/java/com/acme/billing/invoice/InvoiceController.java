package com.acme.billing.invoice;

import java.math.BigDecimal;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/invoices")
public class InvoiceController {
    private final InvoiceService service;

    public InvoiceController(InvoiceService service) {
        this.service = service;
    }

    public record CreateInvoiceRequest(String customerId, BigDecimal total) { }

    @PostMapping
    public ResponseEntity<Long> create(@RequestBody CreateInvoiceRequest request) {
        Invoice invoice = service.create(request.customerId(), request.total());
        return ResponseEntity.ok(invoice.getId());
    }
}
